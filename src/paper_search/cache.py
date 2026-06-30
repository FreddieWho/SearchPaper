import hashlib
import json
import sqlite3
import time
from typing import Any, Optional


class Cache:
    def __init__(self, db_path: Optional[str] = None, default_ttl_seconds: int = 86400):
        self.db_path = db_path or "/tmp/paper_search_cache.db"
        self.default_ttl = default_ttl_seconds
        self._init_db()

    def _init_db(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache (
                    key TEXT PRIMARY KEY,
                    source TEXT NOT NULL,
                    endpoint TEXT NOT NULL,
                    params_hash TEXT NOT NULL,
                    fields_hash TEXT NOT NULL,
                    value TEXT NOT NULL,
                    expires_at REAL NOT NULL,
                    created_at REAL NOT NULL
                )
                """
            )
            conn.execute(
                "CREATE INDEX IF NOT EXISTS idx_cache_lookup ON cache(source, endpoint, params_hash, fields_hash)"
            )

    @staticmethod
    def _hash(obj: Any) -> str:
        return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

    def _make_key(self, source: str, endpoint: str, params: Any, fields: Optional[list[str]]) -> str:
        return f"{source}:{endpoint}:{self._hash(params)}:{self._hash(fields or [])}"

    def get(self, source: str, endpoint: str, params: Any, fields: Optional[list[str]]):
        key = self._make_key(source, endpoint, params, fields)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute(
                "SELECT value, expires_at FROM cache WHERE key = ?", (key,)
            ).fetchone()
        now = time.time()
        if row and row[1] > now:
            return json.loads(row[0]), {"from_cache": True, "cache_key": key}
        return None, {"from_cache": False, "cache_key": key}

    def set(
        self,
        source: str,
        endpoint: str,
        params: Any,
        fields: Optional[list[str]],
        value: Any,
        ttl_seconds: Optional[int] = None,
    ):
        key = self._make_key(source, endpoint, params, fields)
        ttl = ttl_seconds or self.default_ttl
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO cache(key, source, endpoint, params_hash, fields_hash, value, expires_at, created_at)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                ON CONFLICT(key) DO UPDATE SET
                    value=excluded.value,
                    expires_at=excluded.expires_at,
                    created_at=excluded.created_at
                """,
                (
                    key,
                    source,
                    endpoint,
                    self._hash(params),
                    self._hash(fields or []),
                    json.dumps(value, default=str),
                    now + ttl,
                    now,
                ),
            )

    def clear(self):
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache")
