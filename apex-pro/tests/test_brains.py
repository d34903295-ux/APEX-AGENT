from __future__ import annotations

import pytest

from apex.brains.base import Brain
from apex.brains.contracts import (BrainResult, BrainTask, CostInfo, Risk,
                                    TaskKind, Tier)
from apex.brains.cost import CostMeter, TaskBudget
from apex.brains.council import Council
from apex.brains.memory import LongTermMemory, ShortTermMemory
from apex.brains.router import Router
from apex.brains.specialists import (AnalysisBrain, DecisionBrain,
                                      GenerationBrain, VerifierBrain)


def _uptrend(n=220, slope=0.006):
    out, p = [], 100.0
    for _ in range(n):
        p *= 1 + slope
        out.append(p)
    return out


# ---- contracts / cost -------------------------------------------------------
def test_cost_and_budget():
    b = TaskBudget(1000)
    assert b.can_afford(Tier.LOCAL)            # local always free
    assert b.can_afford(Tier.CHEAP, 800)
    b.charge(CostInfo(tier=Tier.CHEAP, tokens=900))
    assert b.remaining == 100
    assert not b.can_afford(Tier.PREMIUM, 800)  # over budget
    m = CostMeter()
    m.add(CostInfo(tier=Tier.PREMIUM, tokens=1000))
    assert m.spent_usd > 0 and m.spent_tokens == 1000


# ---- router -----------------------------------------------------------------
@pytest.mark.asyncio
async def test_router_low_risk_local_only():
    r = Router([AnalysisBrain()])
    task = BrainTask(TaskKind.ANALYZE, risk=Risk.LOW)
    cands = await r.candidates(task)
    assert [b.name for b in cands] == ["analysis"]


@pytest.mark.asyncio
async def test_router_skips_unhealthy_llm_without_key():
    from apex.brains.council import default_brains
    r = Router(default_brains(include_llm=True))
    # No ANTHROPIC key in tests -> LLM brains are unhealthy -> only locals remain.
    cands = await r.candidates(BrainTask(TaskKind.ANALYZE, risk=Risk.CRITICAL))
    assert all(b.tier is Tier.LOCAL for b in cands)
    assert "analysis" in [b.name for b in cands]


# ---- specialists ------------------------------------------------------------
@pytest.mark.asyncio
async def test_analysis_reads_uptrend_direction():
    a = await AnalysisBrain().handle(BrainTask(TaskKind.ANALYZE,
        payload={"symbol": "BTC/USDT", "prices": _uptrend()}))
    assert a.output["direction"] == 1.0
    assert a.output["regime"] in {"calm", "normal", "volatile", "abnormal"}


@pytest.mark.asyncio
async def test_generation_then_verify_consistent():
    analysis = {"symbol": "BTC/USDT", "direction": 1.0, "confidence": 0.7, "regime": "normal"}
    g = await GenerationBrain().handle(BrainTask(TaskKind.GENERATE,
        payload={"symbol": "BTC/USDT", "analysis": analysis, "facts": {"BTC/USDT": {}}}))
    assert g.output["action"] == "propose_rule"
    assert g.output["rule"]["side"] == "buy"
    assert g.output["rule"]["sandboxed"] is True

    v = await VerifierBrain().handle(BrainTask(TaskKind.VALIDATE, payload={
        "target_kind": TaskKind.GENERATE.value, "target_output": g.output,
        "analysis": analysis, "facts": {"BTC/USDT": {}}}))
    assert v.output["verified"] is True


@pytest.mark.asyncio
async def test_verifier_refutes_contradicting_rule():
    bad = {"action": "propose_rule", "rule": {
        "name": "x", "symbol": "BTC/USDT", "side": "sell",
        "conditions": [{"fact": "BTC/USDT.pred_direction", "op": ">", "value": 0}],
        "leverage": 1.0, "target_pct": 0.02, "sandboxed": True}}
    v = await VerifierBrain().handle(BrainTask(TaskKind.VALIDATE, payload={
        "target_kind": TaskKind.GENERATE.value, "target_output": bad,
        "analysis": {"direction": 1.0}, "facts": {"BTC/USDT": {}}}))
    assert v.output["verified"] is False
    assert any("contradicts" in r for r in v.output["reasons"])


# ---- memory -----------------------------------------------------------------
def test_longterm_memory_scorecard_and_decisions(tmp_path):
    ltm = LongTermMemory(str(tmp_path / "mem.db"))
    assert ltm.score("nobody") == 0.5                # neutral prior
    s1 = ltm.update_score("analysis", 0.0)           # seed low
    s2 = ltm.update_score("analysis", 1.0)           # EWMA moves up toward 1
    assert s2 > s1
    ltm.record_decision({"task_id": "t1", "kind": "decide", "confidence": 0.7,
                         "verified": True, "brains_used": ["analysis"],
                         "consensus": 1.0, "cost": {"usd": 0.0}, "output": {"action": "hold"}})
    rec = ltm.recent_decisions("decide", 5)
    assert rec and rec[0]["task_id"] == "t1"
    ltm.close()


# ---- council: fallback chain ------------------------------------------------
class _FailBrain(Brain):
    name = "boom"
    tier = Tier.LOCAL
    kinds = (TaskKind.ANALYZE,)

    async def _run(self, task):
        raise RuntimeError("kaboom")


@pytest.mark.asyncio
async def test_council_run_falls_back_on_error(tmp_path):
    router = Router([_FailBrain(), AnalysisBrain()])
    council = Council(router=router, long=LongTermMemory(str(tmp_path / "m.db")))
    res = await council.run(BrainTask(TaskKind.ANALYZE,
        payload={"symbol": "BTC/USDT", "prices": _uptrend()}))
    assert res.brain == "analysis"            # degraded past the failing brain
    assert "fallback" in res.rationale


# ---- council: full deliberation (offline) -----------------------------------
@pytest.mark.asyncio
async def test_council_deliberate_end_to_end(tmp_path):
    council = Council(long=LongTermMemory(str(tmp_path / "m.db")), include_llm=True)
    facts = {"BTC/USDT": {"pred_direction": 1.0, "pred_confidence": 0.8}}
    decision = await council.deliberate("BTC/USDT", facts, _uptrend(), risk=Risk.HIGH)
    assert decision.output["action"] in {"propose_rule", "hold"}
    assert "analysis" in decision.brains_used
    assert "decision" in decision.brains_used
    assert decision.consensus is not None
    if decision.output["action"] == "propose_rule":
        assert decision.verified is True
        assert decision.output["rule"]["sandboxed"] is True
