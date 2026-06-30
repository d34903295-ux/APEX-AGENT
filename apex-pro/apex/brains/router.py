"""Router: classify a task and order candidate brains by cost/complexity.

Routing policy
--------------
* Complexity (from task.risk) caps the most expensive tier allowed:
    LOW -> LOCAL only ; MEDIUM -> up to CHEAP ; HIGH/CRITICAL -> up to PREMIUM.
* Within the cap, the most capable healthy brain goes FIRST (it's justified),
  then we degrade toward LOCAL — which is always healthy, guaranteeing a
  non-empty chain. So a simple task never burns premium tokens, and a complex
  one tries the strong brain but still has a free fallback.
"""
from __future__ import annotations

from apex.brains.base import Brain
from apex.brains.contracts import BrainTask, Risk, TaskKind, Tier

RISK_MAX_TIER = {
    Risk.LOW: Tier.LOCAL,
    Risk.MEDIUM: Tier.CHEAP,
    Risk.HIGH: Tier.PREMIUM,
    Risk.CRITICAL: Tier.PREMIUM,
}


class Router:
    def __init__(self, brains: list[Brain] | None = None):
        self.brains: list[Brain] = list(brains or [])

    def register(self, brain: Brain) -> None:
        self.brains.append(brain)

    def max_tier(self, task: BrainTask) -> Tier:
        return RISK_MAX_TIER[task.risk]

    async def candidates(self, task: BrainTask) -> list[Brain]:
        """Healthy brains for this kind within the tier cap, best-first then
        degrading to local. Awaits health() so unconfigured LLMs are skipped."""
        cap = self.max_tier(task).rank
        eligible = [b for b in self.brains if b.handles(task.kind) and b.tier.rank <= cap]
        healthy = [b for b in eligible if await b.health()]
        # best (highest tier) first, then degrade; stable for equal tiers.
        healthy.sort(key=lambda b: b.tier.rank, reverse=True)
        return healthy

    async def ensemble(self, task: BrainTask) -> list[Brain]:
        """All healthy eligible brains for a kind (for consensus/voting)."""
        return await self.candidates(task)
