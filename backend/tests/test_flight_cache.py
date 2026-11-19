import unittest
from types import SimpleNamespace
from concurrent.futures import ThreadPoolExecutor
from threading import Event
from unittest.mock import patch
from app.research_agent.tools.flight_cache import FlightCache

class CacheTests(unittest.TestCase):
    def setUp(self):
        self.cache = FlightCache(2)
        self.calls = 0
    def loader(self):
        self.calls += 1
        return SimpleNamespace(errors=[], flights=[SimpleNamespace(status='found', data={})])
    def get(self, key='a', **kwargs):
        return self.cache.get(key, self.loader, **({'mode':'synthetic','enabled':True}|kwargs))
    def test_hit_and_copy(self):
        self.get().flights[0].data['bad']=1
        self.assertEqual(self.get().flights[0].data,{})
        self.assertEqual(self.calls,1)
    def test_live_bypass(self):
        self.get(mode='live'); self.get(mode='live'); self.assertEqual(self.calls,2)
    def test_disabled(self):
        self.get(enabled=False); self.get(enabled=False); self.assertEqual(self.calls,2)
    def test_expiration(self):
        with patch('app.research_agent.tools.flight_cache.monotonic',return_value=0): self.get()
        with patch('app.research_agent.tools.flight_cache.monotonic',return_value=16): self.get()
        self.assertEqual(self.calls,2)
    def test_eviction(self):
        self.get('a'); self.get('b'); self.get('c'); self.get('a'); self.assertEqual(self.calls,4)
    def test_errors_not_cached(self):
        def bad():
            self.calls+=1
            return SimpleNamespace(errors=['bad'],flights=[])
        for _ in range(2): self.cache.get('a',bad,mode='synthetic',enabled=True)
        self.assertEqual(self.calls,2)
    def test_exception_recovery(self):
        def bad(): raise RuntimeError('test')
        with self.assertRaises(RuntimeError): self.cache.get('a',bad,mode='synthetic',enabled=True)
        self.get(); self.assertEqual(self.calls,1)
    def test_concurrent(self):
        started, release = Event(), Event()
        def slow():
            started.set(); release.wait(3); return self.loader()
        def run(): return self.cache.get('a',slow,mode='synthetic',enabled=True)
        with ThreadPoolExecutor(2) as pool:
            a=pool.submit(run); self.assertTrue(started.wait(2)); b=pool.submit(run); release.set(); a.result(3); b.result(3)
        self.assertEqual(self.calls,1)
