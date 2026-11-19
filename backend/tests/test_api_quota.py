"""Offline quota tests. All databases are temporary."""
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from unittest.mock import patch
from app.research_agent.tools import api_quota as module


class ApiQuotaTests(unittest.TestCase):
    def setUp(self):
        temp = tempfile.TemporaryDirectory()
        self.addCleanup(temp.cleanup)
        self.path = Path(temp.name) / 'quota.db'
        self.q = module.ApiQuota(self.path)

    def reserve(self, provider='cirium', category='status', endpoint='arrival', **kwargs):
        return self.q.reserve(provider, category, endpoint,
                              **({'limit': 3, 'mode': 'live'} | kwargs))

    def usage(self):
        return self.q.usage('cirium', 'status')

    def test_01_initialization(self):
        self.assertTrue(self.path.is_file())
        self.assertEqual(self.usage(), {'used': 0, 'cooldown_until': 0, 'endpoints': {}})

    def test_02_reservation(self):
        result = self.reserve()
        self.assertTrue(result.allowed)
        self.assertEqual((result.used, result.remaining), (1, 2))

    def test_03_exhaustion(self):
        for _ in range(3): self.assertTrue(self.reserve().allowed)
        self.assertEqual(self.reserve().reason, 'budget_exhausted')
        self.assertEqual(self.usage()['used'], 3)

    def test_04_zero_budget(self):
        self.assertFalse(self.reserve(limit=0).allowed)
        self.assertEqual(self.usage()['used'], 0)

    def test_05_synthetic(self):
        self.assertTrue(self.reserve(limit=0, mode='synthetic').allowed)
        self.assertEqual(self.usage()['endpoints'], {})

    def test_06_persistence(self):
        self.reserve()
        self.q = module.ApiQuota(self.path)
        self.assertEqual(self.reserve().used, 2)

    def test_07_endpoints(self):
        self.reserve(); self.reserve(endpoint='departure'); self.reserve()
        self.assertEqual(self.usage()['endpoints'], {'arrival': 2, 'departure': 1})

    def test_08_provider_isolation(self):
        self.reserve(limit=1)
        self.assertTrue(self.reserve(provider='opensky', limit=1).allowed)

    def test_09_category_isolation(self):
        self.reserve(limit=1)
        self.assertTrue(self.reserve(category='other', limit=1).allowed)

    def test_10_cooldown(self):
        self.reserve()
        self.q.cooldown('cirium', 'status')
        self.assertEqual(self.reserve(endpoint='departure').reason, 'cooldown')
        self.assertEqual(self.usage()['used'], 1)

    def test_11_expiry(self):
        with patch.object(module.time, 'time', return_value=1000):
            self.q.cooldown('cirium', 'status', seconds=30)
        with patch.object(module.time, 'time', return_value=1031):
            self.assertTrue(self.reserve().allowed)

    def test_12_cooldown_persistence(self):
        self.q.cooldown('cirium', 'status')
        self.q = module.ApiQuota(self.path)
        self.assertEqual(self.reserve().reason, 'cooldown')

    def test_13_no_shortening(self):
        self.q.cooldown('cirium', 'status', seconds=600)
        until = self.usage()['cooldown_until']
        self.q.cooldown('cirium', 'status', seconds=1)
        self.assertEqual(self.usage()['cooldown_until'], until)

    def test_14_initial_used(self):
        self.assertEqual(self.reserve(limit=10, initial_used=7).used, 8)

    def test_15_no_duplicate_seed(self):
        self.reserve(limit=10, initial_used=7)
        self.assertEqual(self.reserve(limit=10, initial_used=7).used, 9)

    def test_16_concurrency(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.reserve(limit=5), range(30)))
        self.assertEqual(sum(r.allowed for r in results), 5)
        self.assertEqual(self.usage()['used'], 5)
        self.assertEqual(self.usage()['endpoints'], {'arrival': 5})

    def test_17_invalid_budget(self):
        for kwargs in ({'limit': -1}, {'limit': True}, {'initial_used': -1}, {'limit': 1.5}):
            with self.subTest(kwargs=kwargs), self.assertRaises(ValueError): self.reserve(**kwargs)

    def test_18_invalid_mode(self):
        with self.assertRaises(ValueError): self.reserve(mode='invalid')

    def test_19_invalid_cooldown(self):
        for seconds in (0, -1, True, float('nan'), float('inf')):
            with self.subTest(seconds=seconds), self.assertRaises(ValueError):
                self.q.cooldown('cirium', 'status', seconds=seconds)

    def test_20_key_normalization(self):
        self.reserve(provider=' CIRIUM ', category='STATUS', endpoint=' Arrival ')
        self.assertEqual(self.usage()['endpoints'], {'arrival': 1})
        with self.assertRaises(ValueError): self.reserve(provider=' ')


if __name__ == '__main__': unittest.main()
