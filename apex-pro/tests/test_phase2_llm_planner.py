from __future__ import annotations

from apex.ai.llm_planner import (
    LLMRuleProposer, MAX_LEVERAGE, MAX_TARGET_PCT, _extract_json, validate_rule,
)


def _good_rule():
    return {
        "name": "btc_dip_buy_eth",
        "symbol": "ETH/USDT", "side": "buy",
        "conditions": [{"fact": "BTC/USDT.pred_direction", "op": "<", "value": 0}],
        "leverage": 2.0, "target_pct": 0.03,
    }


def test_validate_good_rule_forces_sandbox():
    r = validate_rule(_good_rule())
    assert r is not None
    assert r["sandboxed"] is True            # non-negotiable
    assert r["meta"]["source"] == "llm"
    assert r["side"] == "buy"


def test_validate_clamps_leverage_and_size():
    d = _good_rule()
    d["leverage"] = 999
    d["target_pct"] = 5.0
    r = validate_rule(d)
    assert r["leverage"] == MAX_LEVERAGE
    assert r["target_pct"] == MAX_TARGET_PCT


def test_validate_rejects_bad_operator():
    d = _good_rule()
    d["conditions"][0]["op"] = "DROP TABLE"
    assert validate_rule(d) is None


def test_validate_rejects_unknown_fact_when_whitelisted():
    d = _good_rule()
    assert validate_rule(d, allowed_facts={"ETH/USDT.price"}) is None
    ok = validate_rule(d, allowed_facts={"BTC/USDT.pred_direction"})
    assert ok is not None


def test_validate_rejects_missing_side_or_conditions():
    assert validate_rule({"symbol": "X", "side": "hodl", "conditions": []}) is None
    assert validate_rule({"symbol": "X", "side": "buy", "conditions": []}) is None
    assert validate_rule("not a dict") is None


def test_extract_json_handles_fences_and_prose():
    assert _extract_json('```json\n[{"a":1}]\n```') == [{"a": 1}]
    assert _extract_json('here you go: [{"b":2}] thanks') == [{"b": 2}]
    assert _extract_json("no json here") is None


def test_proposer_noop_without_key():
    p = LLMRuleProposer(api_key="")
    assert p.available is False
    assert p.propose({"BTC/USDT": {"price": 100}}) == []


def test_engine_applies_planner_rule(tmp_path):
    from apex.strategies.engine import StrategyEngine
    from apex.strategies.store import StrategyConfigStore

    store = StrategyConfigStore(str(tmp_path / "c.json")).load(default_roster=["planner"])
    engine = StrategyEngine(symbols=["ETH/USDT"], store=store)
    engine._handle_command({"action": "add_planner_rule", "rule": validate_rule(_good_rule())})
    planner = engine.strategies["planner"]
    assert any(r.name == "btc_dip_buy_eth" for r in planner.rules)
    assert planner.rules[-1].sandboxed is True
