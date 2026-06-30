"""Regression tests for confirmed audit findings (Phase 1)."""
from __future__ import annotations

from apex.config import RiskProfile, Settings
from apex.core.portfolio import Portfolio
from apex.risk.manager import RiskManager
from apex.strategies.engine import StrategyEngine
from apex.strategies.store import StrategyConfigStore


def _engine_with_planner(tmp_path):
    store = StrategyConfigStore(str(tmp_path / "c.json")).load(default_roster=["planner"])
    return StrategyEngine(symbols=["ETH/USDT"], store=store)


# --- #5: add_planner_rule must NOT trust the bus -----------------------------
def test_injected_unsafe_rule_is_rejected(tmp_path):
    engine = _engine_with_planner(tmp_path)
    before = len(engine.strategies["planner"].rules)
    # malformed operator -> validate_rule returns None -> must be rejected
    engine._handle_command({"action": "add_planner_rule", "rule": {
        "symbol": "ETH/USDT", "side": "buy",
        "conditions": [{"fact": "ETH/USDT.x", "op": "DROP", "value": 1}]}})
    assert len(engine.strategies["planner"].rules) == before


def test_injected_rule_is_resanitised(tmp_path):
    engine = _engine_with_planner(tmp_path)
    # An over-leveraged, NON-sandboxed rule off the bus must be clamped + sandboxed.
    engine._handle_command({"action": "add_planner_rule", "rule": {
        "name": "evil", "symbol": "ETH/USDT", "side": "buy", "leverage": 999,
        "target_pct": 5.0, "sandboxed": False,
        "conditions": [{"fact": "ETH/USDT.pred_direction", "op": ">", "value": 0}]}})
    r = engine.strategies["planner"].rules[-1]
    assert r.sandboxed is True
    assert r.leverage <= 5.0
    assert r.target_pct <= 0.10


def test_unknown_command_action_is_ignored(tmp_path):
    engine = _engine_with_planner(tmp_path)
    # must not raise
    engine._handle_command({"action": "totally_unknown", "x": 1})


# --- #2/#10/#20: runtime risk-profile change --------------------------------
def test_set_profile_changes_limits_at_runtime():
    rm = RiskManager(settings=Settings(), portfolio=Portfolio(cash=10_000.0))
    base_lev = rm.limits.max_portfolio_leverage
    assert rm.set_profile("aggressive") is True
    assert rm.limits.max_portfolio_leverage == 5.0
    assert rm.limits.max_portfolio_leverage != base_lev
    assert rm.profile is RiskProfile.AGGRESSIVE


def test_set_profile_rejects_unknown():
    rm = RiskManager(settings=Settings(), portfolio=Portfolio(cash=10_000.0))
    lev = rm.limits.max_portfolio_leverage
    assert rm.set_profile("not-a-profile") is False
    assert rm.limits.max_portfolio_leverage == lev   # unchanged
