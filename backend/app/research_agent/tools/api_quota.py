"""Persistent local weighted API budgets; not provider billing balances."""
from contextlib import closing
from dataclasses import dataclass
from pathlib import Path
import sqlite3
import time
import math
from uuid import uuid4

DB_PATH = Path(__file__).resolve().parents[2] / 'data' / 'api_quota.db'

@dataclass(frozen=True)
class QuotaDecision:
    allowed: bool
    reason: str
    used: int
    remaining: int
    request_id: str | None = None

class ApiQuota:
    def __init__(self, db_path=DB_PATH):
        self.path = Path(db_path)
        self.path.parent.mkdir(parents=True, exist_ok=True)
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            db.execute('CREATE TABLE IF NOT EXISTS quota (provider TEXT, category TEXT, used INTEGER NOT NULL DEFAULT 0, cooldown_until REAL NOT NULL DEFAULT 0, PRIMARY KEY(provider, category))')
            db.execute('CREATE TABLE IF NOT EXISTS endpoint_usage (provider TEXT, category TEXT, endpoint TEXT, attempts INTEGER NOT NULL DEFAULT 0, credits INTEGER NOT NULL DEFAULT 0, legacy_attempts INTEGER NOT NULL DEFAULT 0, PRIMARY KEY(provider, category, endpoint))')

            db.execute("CREATE TABLE IF NOT EXISTS pending_request (provider TEXT, category TEXT, request_id TEXT NOT NULL, PRIMARY KEY(provider, category))")

            columns = {row[1] for row in db.execute('PRAGMA table_info(endpoint_usage)')}
            if 'credits' not in columns and 'legacy_attempts' not in columns:
                db.execute('ALTER TABLE endpoint_usage ADD COLUMN credits INTEGER NOT NULL DEFAULT 0')
                db.execute('ALTER TABLE endpoint_usage ADD COLUMN legacy_attempts INTEGER NOT NULL DEFAULT 0')
                db.execute('UPDATE endpoint_usage SET legacy_attempts=attempts')
            elif not {'credits', 'legacy_attempts'}.issubset(columns):
                raise sqlite3.DatabaseError('Incomplete endpoint accounting schema')

    def _connect(self):
        return sqlite3.connect(self.path, timeout=10)

    @staticmethod
    def _key(value):
        if not isinstance(value, str) or not value.strip():
            raise ValueError('Nonempty quota key required')
        return value.strip().lower()

    def reserve(self, provider, category, endpoint, *, limit, mode, initial_used=0, cost=1, protected=False):
        """Reserve atomically. Every live HTTP attempt requires its own reservation.

        initial_used seeds a new category only; no automatic reset or refund.
        Database errors propagate: callers must block the external request.
        """
        provider, category, endpoint = map(self._key, (provider, category, endpoint))
        if type(limit) is not int or limit < 0 or type(initial_used) is not int or initial_used < 0:
            raise ValueError('Invalid budget')
        if type(cost) is not int or cost <= 0:
            raise ValueError('Invalid credit cost')
        if mode == 'synthetic':
            return QuotaDecision(True, 'synthetic', 0, limit)
        if mode != 'live':
            raise ValueError('Invalid mode')
        db = self._connect()
        try:
            with db:
                db.execute('BEGIN IMMEDIATE')
                db.execute('INSERT OR IGNORE INTO quota(provider,category,used) VALUES(?,?,?)', (provider,category,initial_used))
                used, until = db.execute('SELECT used,cooldown_until FROM quota WHERE provider=? AND category=?',(provider,category)).fetchone()
                if db.execute("SELECT 1 FROM pending_request WHERE provider=? AND category=?", (provider, category)).fetchone():
                    return QuotaDecision(False, "pending_request", used, max(0, limit-used))
                if until > time.time():
                    return QuotaDecision(False,'cooldown',used,max(0,limit-used))
                if used + cost > limit:
                    return QuotaDecision(False,'budget_exhausted',used,max(0,limit-used))
                db.execute('UPDATE quota SET used=used+? WHERE provider=? AND category=?',(cost,provider,category))
                db.execute('INSERT INTO endpoint_usage(provider,category,endpoint,attempts,credits) VALUES(?,?,?,1,?) ON CONFLICT(provider,category,endpoint) DO UPDATE SET attempts=attempts+1,credits=credits+excluded.credits',(provider,category,endpoint,cost))
                request_id = uuid4().hex if protected else None
                if request_id:
                    db.execute("INSERT INTO pending_request VALUES (?,?,?)", (provider, category, request_id))
                return QuotaDecision(True,'reserved',used+cost,limit-used-cost,request_id)
        finally:
            db.close()

    def finalize(self, provider, category, request_id, *, cooldown_seconds=None):
        """Atomically persist outcome and clear only the matching pending marker."""
        provider, category = map(self._key, (provider, category))
        if not isinstance(request_id, str) or not request_id:
            raise ValueError("Missing request ID")
        if cooldown_seconds is not None and (
            isinstance(cooldown_seconds, bool) or not isinstance(cooldown_seconds, (int, float))
            or not math.isfinite(cooldown_seconds) or cooldown_seconds <= 0
            or not math.isfinite(time.time() + cooldown_seconds)
        ):
            raise ValueError("Invalid cooldown")
        with closing(self._connect()) as db, db:
            db.execute("BEGIN IMMEDIATE")
            row = db.execute("SELECT request_id FROM pending_request WHERE provider=? AND category=?", (provider, category)).fetchone()
            if row != (request_id,):
                raise ValueError("Pending request ID mismatch")
            if cooldown_seconds is not None:
                db.execute("UPDATE quota SET cooldown_until=max(cooldown_until,?) WHERE provider=? AND category=?", (time.time()+cooldown_seconds, provider, category))
            db.execute("DELETE FROM pending_request WHERE provider=? AND category=? AND request_id=?", (provider, category, request_id))

    def pending(self, provider, category):
        """Inspect unresolved request ID; never automatically clears it."""
        provider, category = map(self._key, (provider, category))
        with closing(self._connect()) as db:
            row = db.execute("SELECT request_id FROM pending_request WHERE provider=? AND category=?", (provider, category)).fetchone()
            return row[0] if row else None

    def cooldown(self, provider, category, *, seconds=300):
        """Apply category-wide cooldown; never shorten an existing cooldown."""
        provider,category=map(self._key,(provider,category))
        if isinstance(seconds,bool) or not isinstance(seconds,(int,float)) or not math.isfinite(seconds) or seconds <= 0:
            raise ValueError('Invalid cooldown')
        db=self._connect()
        try:
            with db:
                db.execute('INSERT INTO quota(provider,category,cooldown_until) VALUES(?,?,?) ON CONFLICT(provider,category) DO UPDATE SET cooldown_until=max(cooldown_until,excluded.cooldown_until)',(provider,category,time.time()+seconds))
        finally:
            db.close()

    def usage(self, provider, category):
        provider,category=map(self._key,(provider,category))
        db=self._connect()
        try:
            row=db.execute('SELECT used,cooldown_until FROM quota WHERE provider=? AND category=?',(provider,category)).fetchone()
            endpoints=dict(db.execute('SELECT endpoint,attempts FROM endpoint_usage WHERE provider=? AND category=?',(provider,category)))
            return {'used':row[0] if row else 0,'cooldown_until':row[1] if row else 0,'endpoints':endpoints}
        finally:
            db.close()

    def endpoint_accounting(self, provider, category):
        """Known credits since migration; earlier attempt costs remain unknown."""
        provider, category = map(self._key, (provider, category))
        with closing(self._connect()) as db:
            rows = db.execute(
                'SELECT endpoint, attempts, credits, legacy_attempts FROM endpoint_usage WHERE provider=? AND category=?',
                (provider, category),
            ).fetchall()
        return {endpoint: {'attempts': attempts, 'known_credits': credits,
                           'unknown_credit_attempts': legacy,
                           'total_credits': credits if legacy == 0 else None}
                for endpoint, attempts, credits, legacy in rows}
