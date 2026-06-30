"""Persistence layer (audit trail).

Uses SQLAlchemy Core against DATABASE_URL when configured; otherwise falls back
to an append-only JSONL file so nothing is ever lost even with no DB. The
recorder service subscribes to every channel and writes an immutable log.
"""
from __future__ import annotations

import json
import os
import time
from pathlib import Path

from apex.config import get_settings
from apex.core.logging import get_logger

log = get_logger("apex.db")


class JsonlRecorder:
    """Zero-dependency fallback recorder: append-only JSON lines."""

    def __init__(self, path: str = "./data/audit.jsonl"):
        self.path = Path(path)
        self.path.parent.mkdir(parents=True, exist_ok=True)

    def write(self, table: str, row: dict) -> None:
        row = {"_table": table, "_ts": time.time(), **row}
        with self.path.open("a") as f:
            f.write(json.dumps(row, default=str) + "\n")


class SqlRecorder:
    def __init__(self, url: str):
        from sqlalchemy import create_engine, text  # lazy

        self._text = text
        self.engine = create_engine(url, pool_pre_ping=True)
        self._ensure_schema()

    def _ensure_schema(self) -> None:
        schema = Path(__file__).with_name("schema.sql").read_text()
        with self.engine.begin() as conn:
            for stmt in schema.split(";"):
                if stmt.strip() and not stmt.strip().startswith("--"):
                    try:
                        conn.execute(self._text(stmt))
                    except Exception as exc:  # pragma: no cover
                        log.debug("schema stmt skipped: %s", exc)

    def write(self, table: str, row: dict) -> None:
        cols = ", ".join(row)
        vals = ", ".join(f":{c}" for c in row)
        sql = self._text(f"INSERT INTO {table} ({cols}) VALUES ({vals}) ON CONFLICT DO NOTHING")
        try:  # pragma: no cover - DB dependent
            with self.engine.begin() as conn:
                conn.execute(sql, {k: (json.dumps(v) if isinstance(v, (dict, list)) else v)
                                   for k, v in row.items()})
        except Exception as exc:
            log.warning("db write to %s failed: %s", table, exc)


def get_recorder():
    s = get_settings()
    if s.database_url:
        try:
            return SqlRecorder(s.database_url)
        except Exception as exc:  # pragma: no cover
            log.warning("SQL recorder init failed (%s); using JSONL", exc)
    return JsonlRecorder(os.getenv("APEX_AUDIT_PATH", "./data/audit.jsonl"))
