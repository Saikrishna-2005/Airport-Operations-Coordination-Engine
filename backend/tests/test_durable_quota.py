import sqlite3
import tempfile
import unittest
from concurrent.futures import ThreadPoolExecutor
from contextlib import closing
from pathlib import Path
from app.research_agent.tools.api_quota import ApiQuota


class DurableQuotaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'quota.db'
        self.q = ApiQuota(self.path)

    def reserve(self, **kw):
        options = dict(limit=20, mode='live', protected=True, cost=2)
        options.update(kw)
        return self.q.reserve('cirium', 'flight_status', 'arrival', **options)

    def finish(self, request_id, **kw):
        self.q.finalize('cirium', 'flight_status', request_id, **kw)

    def pending(self):
        return self.q.pending('cirium', 'flight_status')

    def sql(self, statement):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(statement)

    def test_01_atomic_reservation(self):
        d = self.reserve()
        self.assertTrue(d.allowed)
        self.assertEqual(self.pending(), d.request_id)
        self.assertEqual(self.q.usage('cirium', 'flight_status')['used'], 2)

    def test_02_pending_blocks(self):
        self.reserve()
        self.assertEqual(self.reserve().reason, 'pending_request')
        self.assertEqual(self.reserve(protected=False).reason, 'pending_request')

    def test_03_restart(self):
        d = self.reserve()
        self.q = ApiQuota(self.path)
        self.assertEqual(self.pending(), d.request_id)
        self.assertFalse(self.reserve().allowed)

    def test_04_finalize(self):
        d = self.reserve()
        self.finish(d.request_id)
        self.assertIsNone(self.pending())
        self.assertEqual(self.reserve().used, 4)

    def test_05_cooldown(self):
        self.finish(self.reserve().request_id, cooldown_seconds=300)
        self.assertIsNone(self.pending())
        self.assertEqual(self.reserve().reason, 'cooldown')

    def test_06_cooldown_write_failure(self):
        d = self.reserve()
        self.sql("CREATE TRIGGER fail_update BEFORE UPDATE OF cooldown_until ON quota BEGIN SELECT RAISE(ABORT, 'injected'); END")
        with self.assertRaises(sqlite3.Error):
            self.finish(d.request_id, cooldown_seconds=300)
        self.sql('DROP TRIGGER fail_update')
        self.q = ApiQuota(self.path)
        self.assertEqual(self.pending(), d.request_id)
        self.assertFalse(self.reserve().allowed)

    def test_07_delete_failure_rolls_back_cooldown(self):
        d = self.reserve()
        self.sql("CREATE TRIGGER fail_delete BEFORE DELETE ON pending_request BEGIN SELECT RAISE(ABORT, 'injected'); END")
        with self.assertRaises(sqlite3.Error):
            self.finish(d.request_id, cooldown_seconds=300)
        self.assertEqual(self.pending(), d.request_id)
        self.assertEqual(self.q.usage('cirium', 'flight_status')['cooldown_until'], 0)

    def test_08_wrong_id(self):
        d = self.reserve()
        with self.assertRaises(ValueError):
            self.finish('wrong')
        self.assertEqual(self.pending(), d.request_id)

    def test_09_marker_insert_failure_rolls_back_credits(self):
        self.sql("CREATE TRIGGER fail_insert BEFORE INSERT ON pending_request BEGIN SELECT RAISE(ABORT, 'injected'); END")
        with self.assertRaises(sqlite3.Error):
            self.reserve()
        self.assertEqual(self.q.usage('cirium', 'flight_status')['used'], 0)
        self.assertEqual(self.q.endpoint_accounting('cirium', 'flight_status'), {})

    def test_10_concurrency(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.reserve(), range(12)))
        self.assertEqual(sum(d.allowed for d in results), 1)
        self.assertEqual(self.q.usage('cirium', 'flight_status')['used'], 2)

    def test_11_synthetic(self):
        self.assertTrue(self.reserve(mode='synthetic').allowed)
        self.assertIsNone(self.pending())
        self.assertEqual(self.q.usage('cirium', 'flight_status')['used'], 0)

    def test_12_category_isolation(self):
        self.reserve()
        d = self.q.reserve('cirium', 'other', 'test', limit=20, mode='live', protected=True)
        self.assertTrue(d.allowed)


if __name__ == '__main__':
    unittest.main()
