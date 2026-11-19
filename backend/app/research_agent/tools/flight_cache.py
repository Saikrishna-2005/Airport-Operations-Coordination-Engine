"""Bounded process-local synthetic cache with single-flight request coalescing."""
from collections import OrderedDict
from concurrent.futures import Future
from copy import deepcopy
from threading import Lock
from time import monotonic


class FlightCache:
    def __init__(self, max_entries=128):
        if max_entries < 1:
            raise ValueError('max_entries must be positive')
        self.max_entries = max_entries
        self._lock = Lock()
        self._entries = OrderedDict()
        self._pending = {}

    def get(self, key, loader, *, mode, ttl=15, enabled=False):
        # Live data must not be retained or shared before licensing approval.
        if mode != 'synthetic' or not enabled or ttl <= 0:
            return loader()
        with self._lock:
            now = monotonic()
            for old in list(self._entries):
                if self._entries[old][0] <= now:
                    del self._entries[old]
            if key in self._entries:
                self._entries.move_to_end(key)
                return deepcopy(self._entries[key][1])
            future = self._pending.get(key)
            owner = future is None
            if owner and len(self._pending) < self.max_entries:
                future = self._pending[key] = Future()
        if future is None:
            return loader()
        if not owner:
            return deepcopy(future.result())
        try:
            result = loader()
            snapshot = deepcopy(result)
            with self._lock:
                if not result.errors and result.flights and all(
                    getattr(f.status, 'value', f.status) == 'found' for f in result.flights
                ):
                    self._entries[key] = (monotonic() + ttl, snapshot)
                    while len(self._entries) > self.max_entries:
                        self._entries.popitem(last=False)
            future.set_result(snapshot)
            return result
        except BaseException as exc:
            future.set_exception(exc)
            raise
        finally:
            with self._lock:
                self._pending.pop(key, None)


flight_cache = FlightCache()
