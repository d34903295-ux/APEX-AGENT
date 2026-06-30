"""LLM-assisted micro-strategy proposer.

Turns the current market context into *candidate* rules for the SymbolicPlanner
(see apex/strategies/planner.py). Design constraints, in order of importance:

  1. SAFE BY CONSTRUCTION. The LLM returns DATA (declarative fact/op/value
     rules), never code. Every proposal is run through `validate_rule`, which
     whitelists operators, clamps leverage/size, and FORCES sandboxed=True.
  2. SANDBOXED. Sandboxed rules can never touch real capital — the risk-manager
     blocks them in live mode. They must pass backtest + 24h paper first.
  3. OPTIONAL. With no ANTHROPIC_API_KEY (or no `anthropic` package) the proposer
     is a silent no-op, so the whole system runs without it.

Even a prompt-injected or hallucinated rule is therefore bounded: worst case it
proposes a sandboxed rule that the risk-manager refuses to fund and that the
hard caps would shrink anyway.
"""
from __future__ import annotations

import json
import re

from apex.config import get_settings
from apex.core.logging import get_logger

log = get_logger("apex.ai.llm")

ALLOWED_OPS = {"<", "<=", ">", ">=", "==", "!="}
MAX_LEVERAGE = 5.0      # proposer is capped low; user raises caps deliberately
MAX_TARGET_PCT = 0.10


def _num(v):
    try:
        return float(v)
    except (TypeError, ValueError):
        return None


def validate_rule(d: dict, allowed_facts: set[str] | None = None) -> dict | None:
    """Return a sanitised, sandboxed rule spec, or None if invalid/unsafe."""
    if not isinstance(d, dict):
        return None
    symbol = d.get("symbol")
    side = str(d.get("side", "")).lower()
    if not isinstance(symbol, str) or side not in {"buy", "sell"}:
        return None

    conditions = []
    for c in d.get("conditions", []):
        if not isinstance(c, dict):
            return None
        fact, op, val = c.get("fact"), c.get("op"), _num(c.get("value"))
        if not isinstance(fact, str) or op not in ALLOWED_OPS or val is None:
            return None
        if allowed_facts is not None and fact not in allowed_facts:
            return None
        conditions.append({"fact": fact, "op": op, "value": val})
    if not conditions:
        return None

    lev = _num(d.get("leverage", 1.0)) or 1.0
    tp = _num(d.get("target_pct", 0.02)) or 0.02
    return {
        "name": str(d.get("name", "llm_rule"))[:64],
        "symbol": symbol,
        "side": side,
        "conditions": conditions,
        "leverage": max(1.0, min(MAX_LEVERAGE, lev)),
        "target_pct": max(0.001, min(MAX_TARGET_PCT, tp)),
        "take_profit": _num(d.get("take_profit")),
        "stop_loss": _num(d.get("stop_loss")),
        "sandboxed": True,                      # ALWAYS — non-negotiable
        "meta": {"source": "llm"},
    }


def _extract_json(text: str):
    """Pull the first JSON array/object out of an LLM response (handles fences)."""
    text = re.sub(r"^```(?:json)?|```$", "", text.strip(), flags=re.MULTILINE).strip()
    try:
        return json.loads(text)
    except Exception:
        m = re.search(r"\[.*\]", text, re.DOTALL)
        if m:
            try:
                return json.loads(m.group(0))
            except Exception:
                return None
    return None


PROMPT = """You are a quantitative strategy assistant. Given the current market \
facts, propose up to {k} short trading micro-rules as STRICT JSON (a list).

Each rule object: {{"name": str, "symbol": str, "side": "buy"|"sell",
"conditions": [{{"fact": str, "op": "<|<=|>|>=|==|!=", "value": number}}],
"leverage": number, "target_pct": number, "take_profit": number|null,
"stop_loss": number|null}}.

ONLY use these fact keys (dotted): {facts}
Return ONLY the JSON list, no prose.

Current facts:
{context}
"""


class LLMRuleProposer:
    def __init__(self, model: str | None = None, api_key: str | None = None):
        s = get_settings()
        self.model = model or s.llm_model
        self.api_key = api_key or s.anthropic_api_key
        self._client = None
        if self.api_key:
            try:
                import anthropic
                self._client = anthropic.Anthropic(api_key=self.api_key)
            except Exception as exc:  # pragma: no cover - optional dep
                log.info("anthropic SDK unavailable (%s); LLM planner disabled", exc)

    @property
    def available(self) -> bool:
        return self._client is not None

    def propose(self, context: dict, *, k: int = 3) -> list[dict]:
        """Return validated, sandboxed rule specs (empty if unavailable/invalid)."""
        if not self.available:
            return []
        allowed_facts = _facts_from_context(context)
        prompt = PROMPT.format(k=k, facts=sorted(allowed_facts),
                               context=json.dumps(context, default=str))
        try:  # pragma: no cover - network
            msg = self._client.messages.create(
                model=self.model, max_tokens=1024,
                messages=[{"role": "user", "content": prompt}])
            text = msg.content[0].text
        except Exception as exc:
            log.warning("LLM proposal failed: %s", exc)
            return []

        parsed = _extract_json(text)
        if not isinstance(parsed, list):
            return []
        rules = [validate_rule(r, allowed_facts) for r in parsed]
        valid = [r for r in rules if r]
        log.info("LLM proposed %d rules, %d valid+sandboxed", len(parsed), len(valid))
        return valid


def _facts_from_context(context: dict) -> set[str]:
    facts: set[str] = set()
    for sym, vals in context.items():
        if isinstance(vals, dict):
            for k in vals:
                facts.add(f"{sym}.{k}")
    return facts
