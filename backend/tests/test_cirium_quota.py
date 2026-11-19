"""Offline provider integration tests. No real HTTP or production DB access."""
import sqlite3
import tempfile
import time
import unittest
from pathlib import Path
from types import SimpleNamespace
from unittest.mock import patch
import httpx
from app.research_agent.tools import cirium_tool as tool
from app.research_agent.tools.api_quota import ApiQuota


class CiriumQuotaTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'quota.db'
        self.quota = ApiQuota(self.path)
        self.config = SimpleNamespace(CIRIUM_ENABLED=True,
            CIRIUM_BASE_URL='https://api.sky.cirium.com', CIRIUM_TIMEOUT_SECONDS=30,
            CIRIUM_REQUEST_BUDGET=10, CIRIUM_INITIAL_USED=0, CIRIUM_COOLDOWN_SECONDS=300)
        def start(target, **kwargs):
            p = patch.object(tool, target, **kwargs)
            self.addCleanup(p.stop)
            return p.start()
        start('settings', new=self.config)
        start('is_cirium_configured', return_value=True)
        start('get_cirium_headers', return_value={'Authorization':'fixture-only'})
        self.factory = start('ApiQuota', side_effect=lambda: ApiQuota(self.path))
        p = patch.object(tool.httpx, 'Client')
        self.addCleanup(p.stop)
        self.client = p.start()
        self.get = self.client.return_value.__enter__.return_value.get
        self.get.side_effect = lambda *a, **k: self.response(200)

    @staticmethod
    def response(status, headers=None):
        return httpx.Response(status, headers=headers, json={'flightStatuses': []},
                              request=httpx.Request('GET', 'https://example.invalid'))

    def lookup(self, mode='live'):
        return tool.get_cirium_flights('DEL', ['AI101'], [], mode=mode)

    def usage(self):
        return self.quota.usage('cirium', 'flight_status')

    def assert_code(self, result, code):
        self.assertIn(code, [error.code for error in result.errors])

    def test_01_synthetic(self):
        self.lookup('synthetic'); self.factory.assert_not_called(); self.client.assert_not_called()
        self.assertEqual(self.usage()['used'], 0)

    def test_02_disabled(self):
        self.config.CIRIUM_ENABLED = False
        self.assert_code(self.lookup(), 'CIRIUM_DISABLED'); self.client.assert_not_called()

    def test_03_zero_budget(self):
        self.config.CIRIUM_REQUEST_BUDGET = 0
        self.assert_code(self.lookup(), 'CIRIUM_BUDGET_EXHAUSTED'); self.client.assert_not_called()

    def test_04_one_credit(self):
        self.config.CIRIUM_REQUEST_BUDGET = 1
        self.assert_code(self.lookup(), 'CIRIUM_BUDGET_EXHAUSTED')
        self.assertEqual(self.get.call_count, 1); self.assertEqual(self.usage()['used'], 1)

    def test_05_two_credits(self):
        self.config.CIRIUM_REQUEST_BUDGET = 2
        self.assertFalse(self.lookup().errors); self.assertEqual(self.get.call_count, 2)
        self.assertEqual(self.usage()['used'], 2)

    def test_06_persistence(self):
        self.config.CIRIUM_REQUEST_BUDGET = 2
        self.lookup(); self.assert_code(self.lookup(), 'CIRIUM_BUDGET_EXHAUSTED')
        self.assertEqual(self.get.call_count, 2)

    def test_07_initial_usage(self):
        self.config.CIRIUM_REQUEST_BUDGET = 10; self.config.CIRIUM_INITIAL_USED = 9
        self.lookup(); self.assertEqual(self.get.call_count, 1); self.assertEqual(self.usage()['used'], 10)

    def test_08_429(self):
        self.get.side_effect = None; self.get.return_value = self.response(429)
        self.assert_code(self.lookup(), 'CIRIUM_HTTP_429'); self.assertEqual(self.get.call_count, 1)
        self.assertGreater(self.usage()['cooldown_until'], time.time()+290)

    def test_09_active_cooldown(self):
        self.quota.cooldown('cirium','flight_status',seconds=300)
        self.assert_code(self.lookup(), 'CIRIUM_COOLDOWN'); self.get.assert_not_called()

    def test_10_retry_after(self):
        self.get.side_effect = None; self.get.return_value = self.response(429, {'Retry-After':'900'})
        self.lookup(); self.assertGreater(self.usage()['cooldown_until'], time.time()+890)

    def test_11_401(self):
        self.get.side_effect = None; self.get.return_value = self.response(401)
        self.assert_code(self.lookup(), 'CIRIUM_HTTP_401'); self.assertEqual(self.get.call_count, 1)

    def test_12_403(self):
        self.get.side_effect = None; self.get.return_value = self.response(403)
        self.assert_code(self.lookup(), 'CIRIUM_HTTP_403'); self.assertEqual(self.get.call_count, 1)

    def test_13_timeout(self):
        self.config.CIRIUM_REQUEST_BUDGET = 1; self.get.side_effect = httpx.ReadTimeout('fixture')
        self.assert_code(self.lookup(), 'CIRIUM_NETWORK_ERROR'); self.assertEqual(self.usage()['used'], 1)
        self.assertEqual(self.get.call_count, 1)

    def test_14_db_failure(self):
        self.factory.side_effect = sqlite3.OperationalError('fixture')
        self.assert_code(self.lookup(), 'CIRIUM_QUOTA_UNAVAILABLE'); self.client.assert_not_called()
        self.factory.side_effect = None; self.factory.return_value = self.quota
        with patch.object(self.quota,'reserve',side_effect=sqlite3.OperationalError('fixture')):
            self.assert_code(self.lookup(), 'CIRIUM_QUOTA_UNAVAILABLE'); self.get.assert_not_called()

    def test_15_endpoints(self):
        self.lookup(); self.assertEqual(self.usage()['endpoints'], {'arrival_airport':1,'departure_airport':1})

if __name__ == '__main__':
    unittest.main()
