"""Local specialist brains — real work, zero cost, always available.

Each has a single responsibility and the shared Brain contract:
  AnalysisBrain   ANALYZE  : prices -> structured market assessment
  GenerationBrain GENERATE : assessment -> a candidate (sandboxed) planner rule
  VerifierBrain   VALIDATE : adversarially refute/confirm another brain's output
  DecisionBrain   DECIDE   : assessment+proposal+verdict -> final go/no-go

These never call the network; they reuse APEX's own indicators/models so the
whole council runs offline. LLM brains (llm_brain.py) plug in at higher tiers.
"""
from __future__ import annotations

from apex.ai.llm_planner import validate_rule
from apex.ai.models import MomentumPredictor
from apex.brains.base import Brain
from apex.brains.contracts import BrainResult, BrainTask, CostInfo, Risk, TaskKind, Tier
from apex.core.indicators import RollingSeries


def _series(prices: list[float]) -> RollingSeries:
    s = RollingSeries(maxlen=max(64, len(prices) + 1))
    for p in prices:
        s.push(p)
    return s


class AnalysisBrain(Brain):
    name = "analysis"
    tier = Tier.LOCAL
    kinds = (TaskKind.ANALYZE,)

    async def _run(self, task: BrainTask) -> BrainResult:
        prices = task.payload.get("prices") or []
        symbol = task.payload.get("symbol", "?")
        if len(prices) < 50:
            return BrainResult.abstain(self.name, task, "insufficient history")
        s = _series(prices)
        pred = MomentumPredictor().predict(symbol, s)
        rsi = s.rsi(14) or 50.0
        vol = s.returns_volatility(20) or 0.0
        regime = ("calm" if vol < 0.0008 else "normal" if vol < 0.004
                  else "volatile" if vol < 0.012 else "abnormal")
        strength = min(1.0, abs(pred["direction"]) * pred["confidence"])
        out = {"symbol": symbol, "direction": pred["direction"],
               "confidence": pred["confidence"], "strength": strength,
               "rsi": rsi, "volatility": vol, "regime": regime}
        return BrainResult(
            brain=self.name, task_id=task.id, kind=task.kind, output=out,
            confidence=pred["confidence"], cost=CostInfo(tier=self.tier),
            rationale=f"{symbol}: dir={pred['direction']} regime={regime} rsi={rsi:.0f}",
        )


class GenerationBrain(Brain):
    name = "generation"
    tier = Tier.LOCAL
    kinds = (TaskKind.GENERATE,)

    def __init__(self, min_confidence: float = 0.55):
        self.min_confidence = min_confidence

    async def _run(self, task: BrainTask) -> BrainResult:
        analysis = task.payload.get("analysis") or {}
        symbol = analysis.get("symbol") or task.payload.get("symbol", "?")
        direction = analysis.get("direction", 0.0)
        conf = analysis.get("confidence", 0.0)
        if not direction or conf < self.min_confidence or analysis.get("regime") == "abnormal":
            return BrainResult(brain=self.name, task_id=task.id, kind=task.kind,
                               output={"action": "hold", "rule": None}, confidence=conf,
                               cost=CostInfo(tier=self.tier),
                               rationale="no actionable edge / abnormal regime")
        side = "buy" if direction > 0 else "sell"
        op = ">" if direction > 0 else "<"
        spec = {
            "name": f"{symbol.split('/')[0].lower()}_{side}_momentum",
            "symbol": symbol, "side": side,
            "conditions": [
                {"fact": f"{symbol}.pred_direction", "op": op, "value": 0},
                {"fact": f"{symbol}.pred_confidence", "op": ">=", "value": round(self.min_confidence, 2)},
            ],
            "leverage": 1.0, "target_pct": round(min(0.05, 0.02 + conf * 0.03), 4),
        }
        rule = validate_rule(spec)   # enforces sandbox + caps
        return BrainResult(
            brain=self.name, task_id=task.id, kind=task.kind,
            output={"action": "propose_rule" if rule else "hold", "rule": rule},
            confidence=conf, cost=CostInfo(tier=self.tier),
            rationale=f"proposed {side} rule for {symbol}",
        )


class VerifierBrain(Brain):
    """Self-critique brain: tries to REFUTE another brain's output."""
    name = "verifier"
    tier = Tier.LOCAL
    kinds = (TaskKind.VALIDATE,)

    async def _run(self, task: BrainTask) -> BrainResult:
        target_kind = task.payload.get("target_kind")
        target = task.payload.get("target_output") or {}
        reasons: list[str] = []
        verified = True

        if target_kind == TaskKind.GENERATE.value:
            rule = target.get("rule")
            if target.get("action") == "hold":
                # holding is always safe/valid
                return BrainResult(brain=self.name, task_id=task.id, kind=task.kind,
                                   output={"verified": True, "reasons": ["hold is safe"]},
                                   confidence=0.9, verified=True, cost=CostInfo(tier=self.tier),
                                   rationale="hold verified")
            if not rule:
                verified, reasons = False, ["no rule / failed validation"]
            else:
                if not rule.get("sandboxed"):
                    verified = False
                    reasons.append("rule not sandboxed")
                analysis = task.payload.get("analysis") or {}
                dirn = analysis.get("direction", 0.0)
                if dirn and ((rule["side"] == "buy") != (dirn > 0)):
                    verified = False
                    reasons.append("rule side contradicts analysis direction")
                facts = set((task.payload.get("facts") or {}).keys())
                if facts:
                    for c in rule.get("conditions", []):
                        base = c["fact"].split(".")[0]
                        if base not in {f.split(".")[0] for f in facts} and "." in c["fact"]:
                            # fact's symbol not in known facts -> can never fire
                            reasons.append(f"condition references unknown fact {c['fact']}")
                            verified = False
        elif target_kind == TaskKind.ANALYZE.value:
            prices = task.payload.get("prices") or []
            if len(prices) >= 50:
                s = _series(prices)
                fast, slow = s.ema(12), s.ema(48)
                independent = 1.0 if (fast or 0) > (slow or 0) else -1.0
                claimed = target.get("direction", 0.0)
                if claimed and independent != claimed:
                    verified = False
                    reasons.append("independent EMA cross disagrees with claimed direction")
            else:
                reasons.append("cannot independently verify (short history)")
        else:
            return BrainResult.abstain(self.name, task, "nothing to verify")

        if verified and not reasons:
            reasons = ["passed all checks"]
        return BrainResult(
            brain=self.name, task_id=task.id, kind=task.kind,
            output={"verified": verified, "reasons": reasons},
            confidence=0.85 if verified else 0.7, verified=verified,
            cost=CostInfo(tier=self.tier), rationale="; ".join(reasons),
        )


class DecisionBrain(Brain):
    name = "decision"
    tier = Tier.LOCAL
    kinds = (TaskKind.DECIDE,)

    async def _run(self, task: BrainTask) -> BrainResult:
        analysis = task.payload.get("analysis") or {}
        generation = task.payload.get("generation") or {}
        validation = task.payload.get("validation") or {}
        verified = bool(validation.get("verified"))
        rule = generation.get("rule")
        conf = float(analysis.get("confidence", 0.0))

        if generation.get("action") == "propose_rule" and rule and verified:
            action, out_rule, reason = "propose_rule", rule, "verified actionable edge"
        else:
            action, out_rule, reason = "hold", None, (
                "unverified" if not verified else "no actionable proposal")
        # Critical-risk decisions demand verification to act at all.
        if task.risk is Risk.CRITICAL and not verified:
            action, out_rule, reason = "hold", None, "critical task requires verification"

        return BrainResult(
            brain=self.name, task_id=task.id, kind=task.kind,
            output={"action": action, "rule": out_rule}, confidence=conf if action != "hold" else 0.0,
            verified=verified, cost=CostInfo(tier=self.tier), rationale=reason,
        )
