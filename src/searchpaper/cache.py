"""SQLite-backed cache and trace storage for SearchPaper."""

from __future__ import annotations

import hashlib
import json
import sqlite3
import time
from pathlib import Path
from typing import Any


class Cache:
    """Local SQLite cache with WAL mode.

    Stores cache entries keyed by source/endpoint/parameters/fields. Also keeps
    lightweight query and source-error trace rows for diagnostics.
    """

    def __init__(self, db_path: str | Path | None = None, default_ttl_seconds: int = 86400):
        if db_path:
            path = Path(db_path).expanduser()
            path.parent.mkdir(parents=True, exist_ok=True)
            self.db_path = str(path)
        else:
            self.db_path = ":memory:"
        self.default_ttl = default_ttl_seconds
        self._init_db()

    def _init_db(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("PRAGMA journal_mode=WAL")
            conn.execute("PRAGMA synchronous=NORMAL")
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS cache_entries (
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
                "CREATE INDEX IF NOT EXISTS idx_cache_lookup "
                "ON cache_entries(source, endpoint, params_hash, fields_hash)"
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS query_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    query TEXT,
                    filters TEXT,
                    sources_requested TEXT,
                    retrieved_at TEXT,
                    cache_policy TEXT,
                    result_count INTEGER
                )
                """
            )
            conn.execute(
                """
                CREATE TABLE IF NOT EXISTS source_error_trace (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    source TEXT NOT NULL,
                    operation TEXT NOT NULL,
                    failure_class TEXT NOT NULL,
                    message TEXT,
                    timestamp TEXT,
                    query_or_identifier TEXT
                )
                """
            )

    @staticmethod
    def _hash(obj: Any) -> str:
        return hashlib.sha256(json.dumps(obj, sort_keys=True, default=str).encode()).hexdigest()

    def _make_key(self, source: str, endpoint: str, params: Any, fields: list[str] | None) -> str:
        return f"{source}:{endpoint}:{self._hash(params)}:{self._hash(fields or [])}"

    def get(
        self, source: str, endpoint: str, params: Any, fields: list[str] | None
    ) -> tuple[Any | None, dict[str, Any]]:
        key = self._make_key(source, endpoint, params, fields)
        with sqlite3.connect(self.db_path) as conn:
            row = conn.execute("SELECT value, expires_at FROM cache_entries WHERE key = ?", (key,)).fetchone()
        now = time.time()
        if row and row[1] > now:
            return json.loads(row[0]), {"from_cache": True, "cache_key": key}
        return None, {"from_cache": False, "cache_key": key}

    def set(
        self,
        source: str,
        endpoint: str,
        params: Any,
        fields: list[str] | None,
        value: Any,
        ttl_seconds: int | None = None,
    ) -> None:
        key = self._make_key(source, endpoint, params, fields)
        ttl = ttl_seconds or self.default_ttl
        now = time.time()
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO cache_entries(
                    key, source, endpoint, params_hash, fields_hash, value, expires_at, created_at
                )
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

    def clear(self) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute("DELETE FROM cache_entries")
            conn.execute("DELETE FROM query_trace")
            conn.execute("DELETE FROM source_error_trace")

    def stats(self) -> dict[str, Any]:
        with sqlite3.connect(self.db_path) as conn:
            total = conn.execute("SELECT COUNT(*) FROM cache_entries").fetchone()[0]
            expired = conn.execute(
                "SELECT COUNT(*) FROM cache_entries WHERE expires_at <= ?", (time.time(),)
            ).fetchone()[0]
            valid = total - expired
            sources = conn.execute("SELECT source, COUNT(*) FROM cache_entries GROUP BY source").fetchall()
        return {
            "total_entries": total,
            "valid_entries": valid,
            "expired_entries": expired,
            "by_source": {s: c for s, c in sources},
            "db_path": self.db_path,
        }

    def log_query_trace(
        self,
        query: str | None,
        filters: dict[str, Any],
        sources_requested: list[str],
        retrieved_at: str,
        cache_policy: str,
        result_count: int,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO query_trace(query, filters, sources_requested, retrieved_at, cache_policy, result_count)
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (
                    query,
                    json.dumps(filters, default=str),
                    ",".join(sources_requested),
                    retrieved_at,
                    cache_policy,
                    result_count,
                ),
            )

    def log_source_error(
        self,
        source: str,
        operation: str,
        failure_class: str,
        message: str,
        timestamp: str,
        query_or_identifier: str | None = None,
    ) -> None:
        with sqlite3.connect(self.db_path) as conn:
            conn.execute(
                """
                INSERT INTO source_error_trace(
                    source, operation, failure_class, message, timestamp, query_or_identifier
                )
                VALUES (?, ?, ?, ?, ?, ?)
                """,
                (source, operation, failure_class, message, timestamp, query_or_identifier),
            )
