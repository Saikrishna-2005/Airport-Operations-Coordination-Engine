"""Offline endpoint accounting and legacy migration tests."""
import sqlite3
import tempfile
import unittest
import time
from contextlib import closing
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.research_agent.tools.api_quota import ApiQuota


class EndpointAccountingTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'quota.db'

    def legacy(self):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('CREATE TABLE quota(provider TEXT, category TEXT, used INTEGER NOT NULL DEFAULT 0, cooldown_until REAL NOT NULL DEFAULT 0, PRIMARY KEY(provider,category))')
            db.execute('CREATE TABLE endpoint_usage(provider TEXT, category TEXT, endpoint TEXT, attempts INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(provider,category,endpoint))')
            db.execute("INSERT INTO quota VALUES('opensky','states',9,0)")
            db.execute("INSERT INTO endpoint_usage VALUES('opensky','states','all',3)")
        return ApiQuota(self.path)

    def reserve(self, q, cost=4, endpoint='all', **kw):
        return q.reserve('opensky','states',endpoint,limit=kw.pop('limit',100),mode=kw.pop('mode','live'),cost=cost,**kw)

    def row(self,q):
        return q.endpoint_accounting('opensky','states')['all']

    def test_01_fresh(self):
        q=ApiQuota(self.path)
        self.assertEqual(q.endpoint_accounting('opensky','states'),{})

    def test_02_weighted(self):
        q=ApiQuota(self.path)
        self.reserve(q,4); self.reserve(q,2)
        self.assertEqual(self.row(q),dict(attempts=2,known_credits=6,unknown_credit_attempts=0,total_credits=6))

    def test_03_legacy(self):
        q=self.legacy()
        self.assertEqual(q.usage('opensky','states')['used'],9)
        self.assertEqual(self.row(q),dict(attempts=3,known_credits=0,unknown_credit_attempts=3,total_credits=None))

    def test_04_post_migration(self):
        q=self.legacy(); self.reserve(q)
        self.assertEqual(self.row(q),dict(attempts=4,known_credits=4,unknown_credit_attempts=3,total_credits=None))
        self.assertEqual(q.usage('opensky','states')['used'],13)

    def test_05_restart(self):
        q=self.legacy(); self.reserve(q)
        self.assertEqual(self.row(q),self.row(ApiQuota(self.path)))

    def test_06_budget_block(self):
        q=ApiQuota(self.path); self.reserve(q)
        self.assertFalse(self.reserve(q,limit=7).allowed)
        self.assertEqual(self.row(q)['known_credits'],4)
        self.assertEqual(self.row(q)['attempts'],1)

    def test_07_synthetic(self):
        q=ApiQuota(self.path); self.reserve(q,mode='synthetic')
        self.assertEqual(q.endpoint_accounting('opensky','states'),{})

    def test_08_cooldown(self):
        q=ApiQuota(self.path); self.reserve(q)
        q.cooldown('opensky','states',seconds=60)
        self.assertFalse(self.reserve(q).allowed)
        self.assertEqual(self.row(q)['known_credits'],4)

    def test_09_endpoint_isolation(self):
        q=ApiQuota(self.path); self.reserve(q); self.reserve(q,2,'other')
        self.assertEqual(q.endpoint_accounting('opensky','states')['other']['total_credits'],2)
        self.assertEqual(self.row(q)['total_credits'],4)

    def test_10_concurrency(self):
        q=ApiQuota(self.path)
        with ThreadPoolExecutor(max_workers=8) as pool:
            results=list(pool.map(lambda _: self.reserve(q,3,limit=30),range(20)))
        self.assertEqual(sum(r.allowed for r in results),10)
        self.assertEqual(self.row(q)['total_credits'],30)
        self.assertEqual(self.row(q)['attempts'],10)

    def test_11_incomplete_schema(self):
        self.legacy()
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute('ALTER TABLE endpoint_usage DROP COLUMN legacy_attempts')
        with self.assertRaises(sqlite3.DatabaseError):
            ApiQuota(self.path)

    def test_12_seed_not_endpoint_cost(self):
        q=ApiQuota(self.path); self.reserve(q,initial_used=12)
        self.assertEqual(q.usage('opensky','states')['used'],16)
        self.assertEqual(self.row(q)['total_credits'],4)

if __name__ == '__main__':
    unittest.main()
