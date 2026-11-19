"""Offline transport tests; no real provider requests or production database."""
import sqlite3
from contextlib import closing
import tempfile
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import Mock, patch
import httpx
from app.research_agent.tools import opensky_dispatcher as d
from app.research_agent.tools.api_quota import ApiQuota
from app.research_agent.tools.opensky_auth import global_auth_manager


class OpenSkyDispatcherTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'quota.db'
        self.q = ApiQuota(self.path)
        self.settings = SimpleNamespace(DATA_MODE='live', FLIGHT_CLIENT_ID='', FLIGHT_CLIENT_SECRET='', OPENSKY_STATES_CREDIT_BUDGET=20, OPENSKY_FLIGHTS_CREDIT_BUDGET=200, OPENSKY_TRACKS_CREDIT_BUDGET=40, OPENSKY_AUTH_BUDGET=10, OPENSKY_COOLDOWN_SECONDS=300)
        for p in (patch.object(d, 'settings', self.settings), patch.object(d, 'ApiQuota', side_effect=lambda: ApiQuota(self.path))):
            p.start(); self.addCleanup(p.stop)
        global_auth_manager.clear(); self.addCleanup(global_auth_manager.clear)
        self.client = Mock(spec=httpx.Client)
        self.client.get.return_value = httpx.Response(200, json={'states': []})
        self.client.post.return_value = httpx.Response(200, json={'access_token':'fixture-token','expires_in':1800})
        self.url = d.BASE+'states/all'
        self.box = dict(lamin=0,lamax=1,lomin=0,lomax=1)

    def call(self): return d.dispatch(self.client,self.url,self.box)
    def used(self, category='states'): return self.q.usage('opensky',category)['used']
    def blocked(self, code, fn=None):
        with self.assertRaises(d.DispatchError) as ctx: (fn or self.call)()
        self.assertEqual(ctx.exception.code,code)
    def credentials(self):
        self.settings.FLIGHT_CLIENT_ID='fixture-id'; self.settings.FLIGHT_CLIENT_SECRET='fixture-secret'

    def test_01_state_cost_boundaries(self):
        for side,cost in [(5,1),(6,2),(10,2),(11,3),(20,3),(21,4)]:
            self.assertEqual(d.request_cost(self.url,dict(lamin=0,lamax=side,lomin=0,lomax=side))[2],cost)
        self.assertEqual(d.request_cost(self.url,{})[2],4)
    def test_02_invalid_box(self):
        for params in [{'lamin':0},dict(self.box,lamax=91),dict(self.box,lamax=float('nan'))]:
            with self.assertRaises(ValueError): d.request_cost(self.url,params)
    def test_03_synthetic_blocks(self):
        self.settings.DATA_MODE='synthetic'; self.credentials(); self.blocked('LIVE_DISABLED'); self.client.get.assert_not_called(); self.client.post.assert_not_called()
    def test_04_zero_budget(self):
        self.settings.OPENSKY_STATES_CREDIT_BUDGET=0; self.credentials(); self.blocked('BUDGET_EXHAUSTED'); self.client.get.assert_not_called(); self.client.post.assert_not_called()
    def test_05_success_accounting(self):
        def get(*args,**kwargs):
            self.assertIsNotNone(self.q.pending('opensky','states')); self.assertEqual(self.used(),1); self.assertFalse(kwargs['follow_redirects']); return httpx.Response(200)
        self.client.get.side_effect=get; self.call(); self.assertIsNone(self.q.pending('opensky','states'))
        self.assertEqual(self.q.endpoint_accounting('opensky','states')['states/all']['known_credits'],1)
    def test_06_exhaustion(self):
        self.settings.OPENSKY_STATES_CREDIT_BUDGET=1; self.call(); self.blocked('BUDGET_EXHAUSTED'); self.assertEqual(self.client.get.call_count,1)
    def test_07_rate_limit(self):
        self.client.get.return_value=httpx.Response(429,headers={'Retry-After':'900'}); self.blocked('RATE_LIMITED'); self.blocked('RATE_LIMITED'); self.assertEqual(self.client.get.call_count,1); self.assertIsNone(self.q.pending('opensky','states'))
    def test_08_timeout_pending(self):
        self.client.get.side_effect=httpx.ReadTimeout('fixture'); self.blocked('PENDING_REQUEST'); self.blocked('PENDING_REQUEST'); self.assertEqual(self.client.get.call_count,1); self.assertIsNotNone(ApiQuota(self.path).pending('opensky','states'))
    def test_09_finalize_failure(self):
        self.client.get.return_value=httpx.Response(429)
        with closing(sqlite3.connect(self.path)) as db, db: db.execute("CREATE TRIGGER fail_delete BEFORE DELETE ON pending_request BEGIN SELECT RAISE(ABORT,'fixture'); END")
        self.blocked('QUOTA_UNAVAILABLE'); self.blocked('PENDING_REQUEST'); self.assertEqual(self.client.get.call_count,1)
    def test_10_server_error_retry(self):
        self.client.get.side_effect=[httpx.Response(503),httpx.Response(200)]; self.call(); self.assertEqual(self.used(),2)
    def test_11_auth_refresh(self):
        self.credentials(); self.client.get.side_effect=[httpx.Response(401),httpx.Response(200)]; self.call(); self.assertEqual(self.used(),2); self.assertEqual(self.used('auth'),2)
    def test_12_auth_cache(self):
        self.credentials(); self.call(); self.call(); self.assertEqual(self.client.post.call_count,1); self.assertEqual(self.used('auth'),1)
    def test_13_auth_rate_limit(self):
        self.credentials(); self.client.post.return_value=httpx.Response(429); self.blocked('RATE_LIMITED'); self.blocked('RATE_LIMITED'); self.client.get.assert_not_called(); self.assertEqual(self.client.post.call_count,1)
    def test_14_category_isolation(self):
        self.credentials(); self.call(); d.dispatch(self.client,d.BASE+'flights/arrival',{'begin':100,'end':200,'airport':'VIDP'}); d.dispatch(self.client,d.BASE+'tracks/all',{'time':0,'icao24':'abcdef'}); self.assertEqual([self.used(x) for x in ('states','flights','tracks','auth')],[1,4,4,1])
    def test_15_unknown_endpoint(self):
        self.blocked('INVALID_REQUEST',lambda:d.dispatch(self.client,'https://example.invalid',{})); self.client.get.assert_not_called(); self.client.post.assert_not_called()
    def test_16_quota_failure(self):
        with patch.object(d,'ApiQuota',side_effect=sqlite3.OperationalError('fixture')): self.blocked('QUOTA_UNAVAILABLE')
        self.client.get.assert_not_called()

if __name__=='__main__': unittest.main()
