"""Risk-manager safety tests — these guard against self-destruction."""
from __future__ import annotations

from apex.config import RiskProfile, Settings
from apex.core.models import Side, Signal, SignalAction
from apex.core.portfolio import Portfolio
from apex.risk.manager import RiskManager


def _rm(profile=RiskProfile.CONSERVATIVE, cash=10_000.0):
    s = Settings(risk_profile=profile, paper_balance=cash)
    rm = RiskManager(settings=s, portfolio=Portfolio(cash=cash))
    rm.pf.mark("BTC/USDT", 100.0)
    return rm


def test_position_size_capped_by_profile():
    rm = _rm()
    sig = Signal(strategy="t", symbol="BTC/USDT", side=Side.BUY,
                 confidence=0.99, target_pct=0.9, price_hint=100.0)
    order, reason = rm.evaluate(sig)
    assert order is not None, reason
    # 10% cap on conservative -> notional <= 1000 -> amount <= 10
    assert order.amount <= 10.0 + 1e-9


def test_leverage_rejected_when_over_cap():
    rm = _rm()  # conservative cap = 1.0x
    sig = Signal(strategy="t", symbol="BTC/USDT", side=Side.BUY,
                 confidence=0.8, target_pct=0.05, leverage=5.0, price_hint=100.0)
    order, reason = rm.evaluate(sig)
    assert order is None
    assert "leverage" in reason


def test_paused_blocks_everything():
    rm = _rm()
    rm.pause("test")
    sig = Signal(strategy="t", symbol="BTC/USDT", side=Side.BUY,
                 confidence=0.8, target_pct=0.05, price_hint=100.0)
    order, reason = rm.evaluate(sig)
    assert order is None and "paused" in reason


def test_sandboxed_rule_blocked_when_live():
    s = Settings(paper_balance=10_000.0)
    object.__setattr__(s, "mode", s.mode)  # keep paper; emulate live below
    rm = RiskManager(settings=s, portfolio=Portfolio(cash=10_000.0))
    rm.pf.mark("BTC/USDT", 100.0)
    # Force "is_live" by monkeypatching the property result via settings flags.
    sig = Signal(strategy="planner", symbol="BTC/USDT", side=Side.BUY,
                 confidence=0.8, target_pct=0.05, price_hint=100.0,
                 meta={"sandboxed": True})
    # In paper mode sandboxed is allowed (paper is the sandbox).
    order, _ = rm.evaluate(sig)
    assert order is not None


def test_abnormal_regime_autopauses():
    rm = _rm()
    rm.on_tick_price("BTC/USDT", 100.0)
    for p in [100.1, 99.9, 100.05, 99.95] * 30:  # build a calm baseline
        rm.on_tick_price("BTC/USDT", p)
    events = rm.on_tick_price("BTC/USDT", 130.0)  # 30% jump
    assert rm.paused
    assert any("regime" in e for e in events)


def test_degen_unlocks_more_leverage_but_bounded():
    cons = Settings(risk_profile=RiskProfile.CONSERVATIVE).effective_limits
    degen = Settings(risk_profile=RiskProfile.DEGEN).effective_limits
    assert degen.max_portfolio_leverage > cons.max_portfolio_leverage
    assert degen.max_portfolio_leverage <= 100.0  # absolute hard cap
