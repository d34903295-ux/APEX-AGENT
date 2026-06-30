"""Contracts for the distributed-intelligence ("more brains") layer.

Every brain is a single-responsibility specialist with the SAME input/output
contract, so the Router/Council can treat them uniformly, compose them, verify
them and measure their quality. Plain dataclasses (no heavy deps) so results
travel over the bus and into SQLite memory unchanged.

Contract summary
----------------
  Brain.handle(BrainTask) -> BrainResult        (async, must never raise)
  - BrainTask.kind   : what is being asked (analyze/generate/validate/decide)
  - BrainTask.risk   : low|medium|high|critical  (drives routing + ensembles)
  - BrainTask.budget : max tokens this task may spend across brains
  - BrainResult.confidence in [0,1], .cost (tier+tokens+usd), .verified flag
  - A brain that cannot help returns BrainResult.abstain(...) (never raises).
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def _id() -> str:
    return uuid.uuid4().hex[:12]


def _now() -> float:
    return time.time()


class TaskKind(str, Enum):
    ANALYZE = "analyze"     # read the market / situation -> structured assessment
    GENERATE = "generate"   # propose an action / strategy / rule
    VALIDATE = "validate"   # self-critique: refute or confirm another output
    DECIDE = "decide"       # final go/no-go with confidence


class Risk(str, Enum):
    LOW = "low"
    MEDIUM = "medium"
    HIGH = "high"
    CRITICAL = "critical"

    @property
    def rank(self) -> int:
        return {"low": 0, "medium": 1, "high": 2, "critical": 3}[self.value]


class Tier(str, Enum):
    """Cost tiers. The router prefers the cheapest tier that can do the job."""
    LOCAL = "local"     # deterministic / heuristic — zero cost, always available
    CHEAP = "cheap"     # small LLM (e.g. haiku) — only if a key is configured
    PREMIUM = "premium" # large LLM (e.g. opus) — only when the task justifies it

    @property
    def rank(self) -> int:
        return {"local": 0, "cheap": 1, "premium": 2}[self.value]


# Rough per-1k-token USD estimates for budgeting/alerts (override via config).
TIER_USD_PER_1K = {Tier.LOCAL: 0.0, Tier.CHEAP: 0.001, Tier.PREMIUM: 0.015}


@dataclass
class CostInfo:
    tier: Tier = Tier.LOCAL
    tokens: int = 0

    @property
    def usd(self) -> float:
        return round(TIER_USD_PER_1K.get(self.tier, 0.0) * self.tokens / 1000, 6)

    def to_dict(self) -> dict:
        return {"tier": self.tier.value, "tokens": self.tokens, "usd": self.usd}


@dataclass
class BrainTask:
    kind: TaskKind
    payload: dict[str, Any] = field(default_factory=dict)
    context: dict[str, Any] = field(default_factory=dict)
    risk: Risk = Risk.LOW
    budget_tokens: int = 4000          # hard ceiling across all brains for this task
    deadline_s: float = 8.0
    session: str = "default"
    id: str = field(default_factory=_id)
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["risk"] = self.risk.value
        return d


@dataclass
class BrainResult:
    brain: str
    task_id: str
    kind: TaskKind
    output: dict[str, Any] = field(default_factory=dict)
    confidence: float = 0.0
    cost: CostInfo = field(default_factory=CostInfo)
    latency_s: float = 0.0
    rationale: str = ""
    verified: bool = False
    abstained: bool = False
    error: str | None = None
    ts: float = field(default_factory=_now)

    @classmethod
    def abstain(cls, brain: str, task: BrainTask, reason: str) -> "BrainResult":
        return cls(brain=brain, task_id=task.id, kind=task.kind,
                   confidence=0.0, abstained=True, rationale=reason)

    @classmethod
    def failure(cls, brain: str, task: BrainTask, error: str) -> "BrainResult":
        return cls(brain=brain, task_id=task.id, kind=task.kind,
                   confidence=0.0, abstained=True, error=error,
                   rationale=f"error: {error}")

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["cost"] = self.cost.to_dict()
        return d


@dataclass
class Decision:
    """The Council's verified, cost-accounted final answer for a task."""
    task_id: str
    kind: TaskKind
    output: dict[str, Any]
    confidence: float
    verified: bool
    brains_used: list[str]
    consensus: float | None        # agreement ratio for ensemble decisions
    cost: CostInfo
    rationale: str
    fallbacks: list[str] = field(default_factory=list)
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict:
        d = asdict(self)
        d["kind"] = self.kind.value
        d["cost"] = self.cost.to_dict()
        return d
