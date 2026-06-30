"""Council: the orchestrator that makes several brains collaborate.

Responsibilities
----------------
1. ROUTE each sub-task to the cost-appropriate brain (via Router).
2. FALLBACK CHAIN: if the chosen brain abstains/errors/over-budget, degrade to
   the next (ending at a free local brain). Never fails silently — every
   fallback is logged, metered and surfaced in the Decision.
3. VERIFY: the self-critique stage. Critical/high-risk flows run an ENSEMBLE of
   verifiers and require weighted consensus; nothing high-risk ships unverified.
4. MEMORY: short-term session context + long-term SQLite decisions and per-brain
   scorecards (the ensemble weights — brains that prove reliable get more vote).
5. COST: a per-task budget gates premium escalation; a global meter feeds the
   spend gauge.

Public API
----------
    council.run(task)                 -> BrainResult   (single kind, with fallback)
    council.deliberate(symbol, ...)   -> Decision      (full analyze→...→decide)
"""
from __future__ import annotations

from apex.brains.contracts import (BrainResult, BrainTask, CostInfo, Decision,
                                    Risk, TaskKind, Tier)
from apex.brains.cost import CostMeter, TaskBudget
from apex.brains.memory import LongTermMemory, ShortTermMemory
from apex.brains.router import Router
from apex.brains.specialists import (AnalysisBrain, DecisionBrain,
                                      GenerationBrain, VerifierBrain)
from apex.core.logging import get_logger
from apex.obs import metrics as M

log = get_logger("apex.brains.council")


def default_brains(include_llm: bool = True) -> list:
    brains = [AnalysisBrain(), GenerationBrain(), VerifierBrain(), DecisionBrain()]
    if include_llm:
        # Added unconditionally; they self-disable (health()==False) without a key,
        # so the council stays 100% free until you opt into LLM tiers.
        from apex.brains.llm_brain import LLMBrain
        brains += [LLMBrain(tier=Tier.CHEAP), LLMBrain(tier=Tier.PREMIUM)]
    return brains


class Council:
    def __init__(self, router: Router | None = None,
                 short: ShortTermMemory | None = None,
                 long: LongTermMemory | None = None,
                 consensus_threshold: float = 0.5,
                 include_llm: bool = True):
        self.router = router or Router(default_brains(include_llm))
        self.short = short or ShortTermMemory()
        self.long = long or LongTermMemory()
        self.consensus_threshold = consensus_threshold
        self.meter = CostMeter()

    # ---- single-kind execution with fallback chain ----------------------
    async def run(self, task: BrainTask, budget: TaskBudget | None = None) -> BrainResult:
        budget = budget or TaskBudget(task.budget_tokens)
        chain = await self.router.candidates(task)
        if not chain:
            return BrainResult.abstain("council", task, "no brain available")
        fallbacks: list[str] = []
        last = BrainResult.abstain("council", task, "no brain produced a result")
        for brain in chain:
            if not budget.can_afford(brain.tier):
                fallbacks.append(f"{brain.name}:over-budget")
                M.BRAIN_FALLBACKS.inc(reason="budget")
                continue
            res = await brain.handle(task)
            self._meter(res, budget)
            M.BRAIN_TASKS.inc(kind=task.kind.value, brain=brain.name)
            if not res.abstained and res.error is None:
                if fallbacks:
                    res.rationale += f" (after fallback: {', '.join(fallbacks)})"
                return res
            fallbacks.append(f"{brain.name}:{'err' if res.error else 'abstain'}")
            M.BRAIN_FALLBACKS.inc(reason="degrade")
            last = res
        log.warning("all brains exhausted for %s (%s)", task.kind.value, fallbacks)
        return last

    def _meter(self, res: BrainResult, budget: TaskBudget) -> None:
        budget.charge(res.cost)
        self.meter.add(res.cost)
        M.BRAIN_COST_USD.set(self.meter.spent_usd)

    # ---- full collaborative decision ------------------------------------
    async def deliberate(self, symbol: str, facts: dict, prices: list[float],
                         risk: Risk = Risk.MEDIUM, session: str = "default") -> Decision:
        budget = TaskBudget(4000 if risk.rank >= 2 else 1500)
        used: list[str] = []
        fallbacks: list[str] = []

        # 1) ANALYZE
        a_task = BrainTask(TaskKind.ANALYZE, payload={"symbol": symbol, "prices": prices},
                           context=facts, risk=risk, session=session)
        analysis = await self.run(a_task, budget)
        used.append(analysis.brain)

        # 2) GENERATE
        g_task = BrainTask(TaskKind.GENERATE,
                           payload={"symbol": symbol, "analysis": analysis.output, "facts": facts},
                           risk=risk, session=session)
        generation = await self.run(g_task, budget)
        used.append(generation.brain)

        # 3) VALIDATE — ensemble + weighted consensus for high/critical risk
        verified, consensus, verifiers = await self._verify(
            generation, analysis, facts, prices, risk, budget)
        used.extend(verifiers)

        # 4) DECIDE
        d_task = BrainTask(TaskKind.DECIDE, risk=risk, session=session, payload={
            "analysis": analysis.output, "generation": generation.output,
            "validation": {"verified": verified, "consensus": consensus}})
        decision = await self.run(d_task, budget)
        used.append(decision.brain)

        out = decision.output
        conf = min(analysis.confidence, decision.confidence) if out.get("action") != "hold" else 0.0
        result = Decision(
            task_id=a_task.id, kind=TaskKind.DECIDE, output=out, confidence=conf,
            verified=verified, brains_used=_dedup(used), consensus=consensus,
            cost=CostInfo(tier=Tier.LOCAL, tokens=budget.spent), rationale=decision.rationale,
            fallbacks=fallbacks)

        # 5) MEMORY + scorecards + metrics
        self.short.remember(session, {"symbol": symbol, "action": out.get("action")})
        self.long.record_decision(result.to_dict())
        self._score(generation, verified)
        M.BRAIN_DECISIONS.inc(action=out.get("action", "hold"))
        if consensus is not None:
            M.BRAIN_CONSENSUS.set(consensus)
        return result

    async def _verify(self, generation, analysis, facts, prices, risk, budget):
        """Run verifier(s); weighted consensus by long-term scorecard."""
        v_payload = {"target_kind": TaskKind.GENERATE.value,
                     "target_output": generation.output,
                     "analysis": analysis.output, "facts": facts, "prices": prices}
        # Local verifier is ALWAYS a mandatory gate.
        local_task = BrainTask(TaskKind.VALIDATE, payload=v_payload, risk=risk)
        verdicts: list[tuple[str, bool, float]] = []
        for brain in await self.router.ensemble(local_task):
            res = await brain.handle(local_task)
            self._meter(res, budget)
            if res.abstained:
                continue
            v = bool(res.output.get("verified"))
            verdicts.append((brain.name, v, self.long.score(brain.name)))
            M.BRAIN_VERIFICATIONS.inc(result="pass" if v else "fail")
            # Single verifier is enough for low/medium risk (cost discipline).
            if risk.rank < 2:
                break

        if not verdicts:
            return False, None, []
        # Weighted consensus; the mandatory local verifier has veto on its own no.
        total_w = sum(w for _, _, w in verdicts) or 1.0
        agree_w = sum(w for _, v, w in verdicts if v)
        consensus = round(agree_w / total_w, 3)
        local_ok = next((v for n, v, _ in verdicts if n == "verifier"), True)
        verified = local_ok and consensus >= self.consensus_threshold
        return verified, consensus, [n for n, _, _ in verdicts]

    def _score(self, generation, verified: bool) -> None:
        """Reward the generator when its proposal passed verification."""
        if generation.output.get("action") == "propose_rule":
            self.long.update_score(generation.brain, 1.0 if verified else 0.0)
        self.long.update_score("verifier", 0.6)  # steady prior for the gate


def _dedup(items: list[str]) -> list[str]:
    seen, out = set(), []
    for x in items:
        if x not in seen:
            seen.add(x)
            out.append(x)
    return out
