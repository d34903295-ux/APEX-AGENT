from __future__ import annotations

from apex.risk.kelly import kelly_fraction, sized_position_pct
from apex.risk.montecarlo import simulate


def test_kelly_bounds():
    assert kelly_fraction(0.5, 1.0) == 0.0      # no edge
    assert 0 < kelly_fraction(0.6, 2.0) <= 1
    assert kelly_fraction(0.9, 0) == 0.0        # invalid ratio


def test_sized_position_respects_cap():
    pct = sized_position_pct(0.99, hard_cap=0.10)
    assert 0 <= pct <= 0.10


def test_montecarlo_detects_ruin_for_negative_edge():
    # Negative expectancy, high vol -> should report meaningful ruin probability.
    res = simulate(-0.02, 0.1, paths=2000, horizon=200, seed=42)
    assert res.prob_ruin > 0.0
    assert not res.safe_to_go_live


def test_montecarlo_safe_for_small_positive_edge():
    res = simulate(0.002, 0.01, paths=2000, horizon=200, seed=1)
    assert res.prob_ruin < 0.05
