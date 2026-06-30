"""Cost awareness + per-operation budgeting for the brain layer.

Every brain call is metered (tokens + USD estimate by tier). A task carries a
token budget; the Council refuses to escalate to a premium brain once the
budget is spent. A global meter feeds the cost gauge/alert.
"""
from __future__ import annotations

from dataclasses import dataclass, field

from apex.brains.contracts import CostInfo, Tier


@dataclass
class CostMeter:
    spent_tokens: int = 0
    spent_usd: float = 0.0
    by_tier: dict[str, int] = field(default_factory=dict)

    def add(self, cost: CostInfo) -> None:
        self.spent_tokens += cost.tokens
        self.spent_usd += cost.usd
        self.by_tier[cost.tier.value] = self.by_tier.get(cost.tier.value, 0) + cost.tokens

    def snapshot(self) -> dict:
        return {"tokens": self.spent_tokens, "usd": round(self.spent_usd, 6),
                "by_tier": dict(self.by_tier)}


class TaskBudget:
    """Tracks remaining token budget for a single task and gates escalation."""

    def __init__(self, total_tokens: int):
        self.total = total_tokens
        self.spent = 0

    @property
    def remaining(self) -> int:
        return max(0, self.total - self.spent)

    def charge(self, cost: CostInfo) -> None:
        self.spent += cost.tokens

    def can_afford(self, tier: Tier, est_tokens: int = 800) -> bool:
        # Local tier is always free and always affordable.
        if tier is Tier.LOCAL:
            return True
        return self.remaining >= est_tokens
