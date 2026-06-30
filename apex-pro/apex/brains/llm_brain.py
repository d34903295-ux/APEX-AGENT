"""LLM-backed brains (cheap / premium tiers).

OPTIONAL by design: a brain is only routable when `health()` is True, which
requires both the `anthropic` package and an API key. With neither, the council
runs entirely on the free local brains — so this never imposes a cost floor.

Cost-aware: reports real token usage from the API response so the budget and
spend alerts are accurate. On any error it ABSTAINS (never raises), letting the
council fall back to a cheaper/local brain.
"""
from __future__ import annotations

import json
import re

from apex.brains.base import Brain
from apex.brains.contracts import BrainResult, BrainTask, CostInfo, TaskKind, Tier
from apex.config import get_settings
from apex.core.logging import get_logger

log = get_logger("apex.brains.llm")

# Default model per tier. Cheap = small/fast; premium = strongest.
TIER_MODELS = {Tier.CHEAP: "claude-haiku-4-5-20251001", Tier.PREMIUM: "claude-opus-4-8"}


def _extract_json(text: str):
    text = re.sub(r"^```(?:json)?|```$", "", (text or "").strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"[\[{].*[\]}]", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


PROMPTS = {
    TaskKind.ANALYZE: (
        "Assess the market for {symbol} from these recent facts. Reply ONLY as JSON "
        '{{"direction": -1|0|1, "confidence": 0..1, "regime": str, "rationale": str}}.\n'
        "Facts: {facts}"
    ),
    TaskKind.VALIDATE: (
        "You are an adversarial reviewer. Try to REFUTE this proposed trading output. "
        'Reply ONLY as JSON {{"verified": bool, "reasons": [str]}}. Default verified=false '
        "if uncertain.\nProposal: {target}\nContext: {facts}"
    ),
    TaskKind.GENERATE: (
        "Propose ONE conservative trading micro-rule as JSON "
        '{{"name": str, "symbol": str, "side": "buy"|"sell", '
        '"conditions": [{{"fact": str, "op": "<|<=|>|>=|==|!=", "value": number}}], '
        '"leverage": number, "target_pct": number}}. Use only facts: {facts}'
    ),
}


class LLMBrain(Brain):
    def __init__(self, tier: Tier = Tier.CHEAP, model: str | None = None,
                 kinds: tuple[TaskKind, ...] = (TaskKind.ANALYZE, TaskKind.GENERATE, TaskKind.VALIDATE)):
        self.tier = tier
        self.kinds = kinds
        self.name = f"llm-{tier.value}"
        self.model = model or TIER_MODELS.get(tier, "claude-opus-4-8")
        self._client = None
        key = get_settings().anthropic_api_key
        if key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=key)
            except Exception as exc:  # pragma: no cover - optional dep
                log.info("anthropic unavailable (%s); %s disabled", exc, self.name)

    async def health(self) -> bool:
        return self._client is not None

    async def _run(self, task: BrainTask) -> BrainResult:
        if self._client is None:
            return BrainResult.abstain(self.name, task, "LLM not configured")
        facts = json.dumps(task.payload.get("facts") or task.context or {}, default=str)[:2000]
        prompt = PROMPTS[task.kind].format(
            symbol=task.payload.get("symbol", "?"), facts=facts,
            target=json.dumps(task.payload.get("target_output") or {}, default=str)[:1500])

        import asyncio
        loop = asyncio.get_event_loop()

        def _call():
            return self._client.messages.create(
                model=self.model, max_tokens=700,
                messages=[{"role": "user", "content": prompt}])

        msg = await loop.run_in_executor(None, _call)
        usage = getattr(msg, "usage", None)
        tokens = (getattr(usage, "input_tokens", 0) + getattr(usage, "output_tokens", 0)) if usage else 700
        parsed = _extract_json(msg.content[0].text) or {}

        out, conf, verified = self._shape(task.kind, parsed)
        return BrainResult(
            brain=self.name, task_id=task.id, kind=task.kind, output=out,
            confidence=conf, verified=verified, cost=CostInfo(tier=self.tier, tokens=int(tokens)),
            rationale=f"{self.name}/{self.model}",
        )

    @staticmethod
    def _shape(kind: TaskKind, parsed: dict):
        if kind is TaskKind.VALIDATE:
            v = bool(parsed.get("verified"))
            return {"verified": v, "reasons": parsed.get("reasons", [])}, 0.8 if v else 0.7, v
        if kind is TaskKind.GENERATE:
            from apex.ai.llm_planner import validate_rule
            rule = validate_rule(parsed) if parsed else None
            return ({"action": "propose_rule" if rule else "hold", "rule": rule},
                    0.7 if rule else 0.3, False)
        # ANALYZE
        return (parsed, float(parsed.get("confidence", 0.5)), False)
