"""Offline integration fault tests; reuses existing Cirium fixture."""
import sqlite3
import time
import unittest
from contextlib import closing
import httpx
import test_cirium_quota as fixtures
from app.research_agent.tools.api_quota import ApiQuota

class CiriumDurableTests(unittest.TestCase):
    setUp = fixtures.CiriumQuotaTests.setUp
    response = staticmethod(fixtures.CiriumQuotaTests.response)
    lookup = fixtures.CiriumQuotaTests.lookup
    usage = fixtures.CiriumQuotaTests.usage
    assert_code = fixtures.CiriumQuotaTests.assert_code

    def pending(self):
        return ApiQuota(self.path).pending('cirium', 'flight_status')

    def sql(self, statement):
        with closing(sqlite3.connect(self.path)) as db, db:
            db.execute(statement)

    def test_01_marker_before_http(self):
        def respond(*args, **kwargs):
            self.assertIsNotNone(self.pending())
            return self.response(200)
        self.get.side_effect = respond
        self.assertFalse(self.lookup().errors)
        self.assertIsNone(self.pending())
        self.assertEqual(self.usage()['used'], 2)

    def test_02_429_finalized(self):
        self.get.side_effect = lambda *a, **k: self.response(429, {'Retry-After':'900'})
        self.assert_code(self.lookup(), 'CIRIUM_HTTP_429')
        self.assertIsNone(self.pending())
        self.assertGreater(self.usage()['cooldown_until'], time.time()+890)
        self.assert_code(self.lookup(), 'CIRIUM_COOLDOWN')
        self.assertEqual(self.get.call_count, 1)

    def test_03_cooldown_write_failure(self):
        self.sql("CREATE TRIGGER fail_cooldown BEFORE UPDATE OF cooldown_until ON quota BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.get.side_effect = lambda *a, **k: self.response(429)
        self.assert_code(self.lookup(), 'CIRIUM_QUOTA_UNAVAILABLE')
        marker = self.pending()
        self.assertIsNotNone(marker)
        self.sql('DROP TRIGGER fail_cooldown')
        self.assert_code(self.lookup(), 'CIRIUM_PENDING_REQUEST')
        self.assertEqual(self.pending(), marker)
        self.assertEqual(self.get.call_count, 1)
        self.assertEqual(self.usage()['used'], 1)

    def test_04_marker_delete_failure(self):
        self.sql("CREATE TRIGGER fail_delete BEFORE DELETE ON pending_request BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.get.side_effect = lambda *a, **k: self.response(429)
        self.assert_code(self.lookup(), 'CIRIUM_QUOTA_UNAVAILABLE')
        self.assertIsNotNone(self.pending())
        self.assertEqual(self.usage()['cooldown_until'], 0)
        self.sql('DROP TRIGGER fail_delete')
        self.assert_code(self.lookup(), 'CIRIUM_PENDING_REQUEST')
        self.assertEqual(self.get.call_count, 1)

    def test_05_success_finalize_failure(self):
        self.sql("CREATE TRIGGER fail_delete BEFORE DELETE ON pending_request BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assert_code(self.lookup(), 'CIRIUM_QUOTA_UNAVAILABLE')
        self.assertIsNotNone(self.pending())
        self.assertEqual(self.get.call_count, 1)
        self.assert_code(self.lookup(), 'CIRIUM_PENDING_REQUEST')
        self.assertEqual(self.get.call_count, 1)

    def test_06_timeout(self):
        self.get.side_effect = httpx.ReadTimeout('injected')
        result = self.lookup()
        self.assert_code(result, 'CIRIUM_NETWORK_ERROR')
        self.assertFalse(result.errors[0].retryable)
        self.assertIsNotNone(self.pending())
        self.assert_code(self.lookup(), 'CIRIUM_PENDING_REQUEST')
        self.assertEqual(self.get.call_count, 1)

    def test_07_marker_insert_failure(self):
        self.sql("CREATE TRIGGER fail_insert BEFORE INSERT ON pending_request BEGIN SELECT RAISE(ABORT, 'injected'); END")
        self.assert_code(self.lookup(), 'CIRIUM_QUOTA_UNAVAILABLE')
        self.get.assert_not_called()
        self.assertEqual(self.usage()['used'], 0)

    def test_08_auth_rejection_finalized(self):
        self.get.side_effect = lambda *a, **k: self.response(401)
        self.assert_code(self.lookup(), 'CIRIUM_HTTP_401')
        self.assertIsNone(self.pending())
        self.assertEqual(self.get.call_count, 1)

    def test_09_synthetic_with_pending(self):
        self.quota.reserve('cirium','flight_status','arrival_airport',limit=10,mode='live',protected=True)
        marker = self.pending()
        self.assertFalse(self.lookup('synthetic').errors)
        self.get.assert_not_called()
        self.assertEqual(self.pending(), marker)
        self.assertEqual(self.usage()['used'], 1)

    def test_10_overlap(self):
        def respond(*args, **kwargs):
            self.assert_code(self.lookup(), 'CIRIUM_PENDING_REQUEST')
            return self.response(200)
        self.get.side_effect = respond
        self.config.CIRIUM_REQUEST_BUDGET = 1
        self.assert_code(self.lookup(), 'CIRIUM_BUDGET_EXHAUSTED')
        self.assertEqual(self.get.call_count, 1)
        self.assertIsNone(self.pending())

if __name__ == '__main__':
    unittest.main()
