from __future__ import annotations

from apex.config import RiskLimits, Settings
from apex.core.models import Fill, Side, Signal
from apex.core.portfolio import Portfolio
from apex.risk.correlation import CorrelationTracker
from apex.risk.manager import RiskManager


def test_correlation_identical_and_inverse():
    ct = CorrelationTracker(window=100)
    p = 100.0
    for k in range(60):
        p *= 1 + (0.002 if k % 2 else -0.0015)
        ct.update("A", p)
        ct.update("B", p)            # identical -> +1
        ct.update("C", 200 - p)      # mirrored -> negative
    assert ct.correlation("A", "B") > 0.95
    assert ct.correlation("A", "C") < -0.5
    assert ct.correlation("A", "A") == 1.0


def _rm_widelimits():
    rm = RiskManager(settings=Settings(paper_balance=10_000.0),
                     portfolio=Portfolio(cash=10_000.0))
    rm.limits = RiskLimits(max_position_pct=0.25, max_portfolio_leverage=1.0,
                           max_daily_drawdown_pct=0.5, max_open_positions=8,
                           max_correlated_exposure_pct=0.30)
    return rm


def _build_correlation(rm, a, b, identical=True):
    p = 100.0
    for k in range(50):
        p *= 1 + (0.0015 if k % 2 else -0.0012)
        rm.correlation.update(a, p)
        rm.correlation.update(b, p if identical else (200 - p))


def test_correlated_cluster_exposure_rejected():
    rm = _rm_widelimits()
    rm.pf.mark("AAA", 100.0)
    rm.pf.mark("BBB", 100.0)
    # Open a ~20% position in AAA.
    rm.on_fill(Fill(order_id="x", symbol="AAA", side=Side.BUY, amount=20, price=100.0))
    assert abs(rm.pf.exposure_pct("AAA") - 0.20) < 0.02
    _build_correlation(rm, "AAA", "BBB", identical=True)

    sig = Signal(strategy="t", symbol="BBB", side=Side.BUY,
                 confidence=0.8, target_pct=0.25, price_hint=100.0)
    order, reason = rm.evaluate(sig)
    assert order is None
    assert "correlated" in reason


def test_uncorrelated_position_allowed():
    rm = _rm_widelimits()
    rm.pf.mark("AAA", 100.0)
    rm.pf.mark("BBB", 100.0)
    rm.on_fill(Fill(order_id="x", symbol="AAA", side=Side.BUY, amount=20, price=100.0))
    _build_correlation(rm, "AAA", "BBB", identical=False)  # inverse/uncorrelated

    sig = Signal(strategy="t", symbol="BBB", side=Side.BUY,
                 confidence=0.8, target_pct=0.20, price_hint=100.0)
    order, reason = rm.evaluate(sig)
    assert order is not None, reason
