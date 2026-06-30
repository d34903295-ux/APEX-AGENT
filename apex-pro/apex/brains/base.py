"""Brain base class. Single responsibility, uniform contract, never raises."""
from __future__ import annotations

import time
from abc import ABC, abstractmethod

from apex.brains.contracts import BrainResult, BrainTask, CostInfo, Tier, TaskKind
from apex.core.logging import get_logger

log = get_logger("apex.brains")


class Brain(ABC):
    #: unique, human-readable
    name: str = "base"
    #: cost tier
    tier: Tier = Tier.LOCAL
    #: which task kinds this brain can handle
    kinds: tuple[TaskKind, ...] = ()

    def handles(self, kind: TaskKind) -> bool:
        return kind in self.kinds

    async def health(self) -> bool:
        """Is this brain usable right now? (e.g. LLM key present)."""
        return True

    @abstractmethod
    async def _run(self, task: BrainTask) -> BrainResult:
        """Do the work. May assume `handles(task.kind)` is True."""

    async def handle(self, task: BrainTask) -> BrainResult:
        """Public entrypoint: times the call and converts any error into a
        failure result. Brains NEVER raise — the Council depends on it."""
        if not self.handles(task.kind):
            return BrainResult.abstain(self.name, task, f"{self.name} does not handle {task.kind.value}")
        start = time.monotonic()
        try:
            result = await self._run(task)
        except Exception as exc:  # noqa: BLE001 - contract: never raise
            log.warning("brain %s failed on %s: %s", self.name, task.id, exc)
            return BrainResult.failure(self.name, task, str(exc))
        result.latency_s = round(time.monotonic() - start, 4)
        if not result.brain:
            result.brain = self.name
        if result.cost is None:
            result.cost = CostInfo(tier=self.tier)
        return result
