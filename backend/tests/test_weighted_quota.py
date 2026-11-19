"""Offline tests for weighted quota reservations."""
import tempfile
import unittest
from pathlib import Path
from concurrent.futures import ThreadPoolExecutor
from app.research_agent.tools.api_quota import ApiQuota


class WeightedQuotaTests(unittest.TestCase):
    def setUp(self):
        self.tmp = tempfile.TemporaryDirectory()
        self.addCleanup(self.tmp.cleanup)
        self.path = Path(self.tmp.name) / 'quota.db'
        self.quota = ApiQuota(self.path)

    def reserve(self, cost=1, limit=10, **kwargs):
        return self.quota.reserve('opensky', 'states', 'states/all',
                                  limit=limit, mode='live', cost=cost, **kwargs)

    def test_01_weighted_reservation(self):
        d = self.reserve(4)
        self.assertEqual((d.allowed, d.used, d.remaining), (True, 4, 6))

    def test_02_mixed_costs(self):
        for cost in (1, 4, 2, 3):
            self.assertTrue(self.reserve(cost).allowed)
        self.assertEqual(self.quota.usage('opensky', 'states')['used'], 10)

    def test_03_insufficient_remaining(self):
        self.reserve(8)
        d = self.reserve(3)
        self.assertEqual((d.allowed, d.reason, d.used, d.remaining), (False, 'budget_exhausted', 8, 2))

    def test_04_exact_budget(self):
        self.assertTrue(self.reserve(10).allowed)
        self.assertFalse(self.reserve().allowed)

    def test_05_invalid_costs(self):
        for cost in (0, -1, True, 1.5, '2', None):
            with self.subTest(cost=cost), self.assertRaises(ValueError):
                self.reserve(cost)

    def test_06_synthetic(self):
        d = self.quota.reserve('opensky', 'states', 'states/all', limit=10, mode='synthetic', cost=4)
        self.assertTrue(d.allowed)
        self.assertEqual(self.quota.usage('opensky', 'states')['used'], 0)

    def test_07_persistence(self):
        self.reserve(4)
        self.quota = ApiQuota(self.path)
        self.assertEqual(self.reserve(2).used, 6)

    def test_08_initial_usage(self):
        self.assertEqual(self.reserve(4, initial_used=5).used, 9)
        self.assertEqual(self.reserve(1, initial_used=5).used, 10)

    def test_09_attempts_not_credits(self):
        self.reserve(4)
        self.reserve(2)
        u = self.quota.usage('opensky', 'states')
        self.assertEqual(u['used'], 6)
        self.assertEqual(u['endpoints'], {'states/all': 2})

    def test_10_category_isolation(self):
        self.reserve(10)
        d = self.quota.reserve('opensky', 'flights', 'flights/all', limit=10, mode='live', cost=4)
        self.assertEqual((d.allowed, d.used), (True, 4))

    def test_11_cooldown(self):
        self.reserve(2)
        self.quota.cooldown('opensky', 'states', seconds=300)
        d = self.reserve(4)
        self.assertEqual((d.allowed, d.reason, d.used), (False, 'cooldown', 2))

    def test_12_concurrent_weighted_reservations(self):
        with ThreadPoolExecutor(max_workers=8) as pool:
            results = list(pool.map(lambda _: self.reserve(3, limit=20), range(20)))
        self.assertEqual(sum(d.allowed for d in results), 6)
        u = self.quota.usage('opensky', 'states')
        self.assertEqual(u['used'], 18)
        self.assertEqual(u['endpoints'], {'states/all': 6})


if __name__ == '__main__':
    unittest.main()
