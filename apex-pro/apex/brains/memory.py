"""Memory for the brain layer: short-term (session) + long-term (persistent).

Deliberately uses the stdlib `sqlite3` for long-term memory — zero extra
dependency, file-backed, and honours the "defer the heavy DB until the domain
demands it" rule. Migrate to Postgres/Timescale later behind the same
`LongTermMemory` interface if scale requires it.

Long-term memory stores every Decision and a rolling per-brain scorecard
(EWMA of a quality signal), which the Router uses as ensemble weights — i.e.
the brains learn which of them to trust over time.
"""
from __future__ import annotations

import json
import sqlite3
import time
from collections import deque
from pathlib import Path
from threading import Lock


class ShortTermMemory:
    """Bounded per-session recent context (in-process, fast)."""

    def __init__(self, maxlen: int = 50):
        self.maxlen = maxlen
        self._by_session: dict[str, deque] = {}

    def remember(self, session: str, item: dict) -> None:
        dq = self._by_session.setdefault(session, deque(maxlen=self.maxlen))
        dq.append({"ts": time.time(), **item})

    def recall(self, session: str, n: int = 10) -> list[dict]:
        return list(self._by_session.get(session, []))[-n:]


class LongTermMemory:
    """SQLite-backed persistent memory + per-brain scorecards (EWMA)."""

    def __init__(self, path: str = "./data/brain_memory.db", ewma_alpha: float = 0.2):
        self.alpha = ewma_alpha
        self._lock = Lock()
        Path(path).parent.mkdir(parents=True, exist_ok=True)
        self.conn = sqlite3.connect(path, check_same_thread=False)
        self.conn.row_factory = sqlite3.Row
        self._init_schema()

    def _init_schema(self) -> None:
        with self._lock, self.conn:
            self.conn.executescript(
                """
                CREATE TABLE IF NOT EXISTS decisions (
                    id INTEGER PRIMARY KEY AUTOINCREMENT,
                    ts REAL NOT NULL,
                    task_id TEXT, kind TEXT, confidence REAL, verified INTEGER,
                    brains TEXT, consensus REAL, cost_usd REAL, output TEXT
                );
                CREATE TABLE IF NOT EXISTS scorecard (
                    brain TEXT PRIMARY KEY,
                    score REAL NOT NULL DEFAULT 0.5,
                    samples INTEGER NOT NULL DEFAULT 0,
                    updated REAL
                );
                CREATE INDEX IF NOT EXISTS idx_decisions_kind ON decisions(kind, ts DESC);
                """
            )

    # ---- decisions ------------------------------------------------------
    def record_decision(self, decision_dict: dict) -> None:
        d = decision_dict
        with self._lock, self.conn:
            self.conn.execute(
                "INSERT INTO decisions (ts,task_id,kind,confidence,verified,brains,consensus,cost_usd,output)"
                " VALUES (?,?,?,?,?,?,?,?,?)",
                (d.get("ts", time.time()), d.get("task_id"), d.get("kind"),
                 d.get("confidence"), int(bool(d.get("verified"))),
                 json.dumps(d.get("brains_used", [])), d.get("consensus"),
                 (d.get("cost") or {}).get("usd", 0.0), json.dumps(d.get("output", {}))),
            )

    def recent_decisions(self, kind: str | None = None, n: int = 10) -> list[dict]:
        with self._lock:
            if kind:
                rows = self.conn.execute(
                    "SELECT * FROM decisions WHERE kind=? ORDER BY ts DESC LIMIT ?", (kind, n)
                ).fetchall()
            else:
                rows = self.conn.execute(
                    "SELECT * FROM decisions ORDER BY ts DESC LIMIT ?", (n,)
                ).fetchall()
        return [dict(r) for r in rows]

    # ---- scorecards (ensemble weights) ----------------------------------
    def update_score(self, brain: str, quality: float) -> float:
        """EWMA-update a brain's quality in [0,1]; returns the new score."""
        quality = max(0.0, min(1.0, quality))
        with self._lock, self.conn:
            row = self.conn.execute("SELECT score,samples FROM scorecard WHERE brain=?", (brain,)).fetchone()
            if row is None:
                new = quality
                self.conn.execute(
                    "INSERT INTO scorecard (brain,score,samples,updated) VALUES (?,?,?,?)",
                    (brain, new, 1, time.time()))
            else:
                new = (1 - self.alpha) * row["score"] + self.alpha * quality
                self.conn.execute(
                    "UPDATE scorecard SET score=?,samples=?,updated=? WHERE brain=?",
                    (new, row["samples"] + 1, time.time(), brain))
        return new

    def score(self, brain: str) -> float:
        with self._lock:
            row = self.conn.execute("SELECT score FROM scorecard WHERE brain=?", (brain,)).fetchone()
        return float(row["score"]) if row else 0.5  # neutral prior

    def close(self) -> None:
        self.conn.close()
