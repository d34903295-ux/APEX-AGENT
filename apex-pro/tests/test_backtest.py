from __future__ import annotations

import math

from apex.backtest.engine import run_backtest
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies import available_strategies  # noqa: F401


def _wave(n=400, base=100.0):
    return [base * (1 + 0.05 * math.sin(i / 10)) for i in range(n)]


def test_backtest_runs_and_reports():
    grid = STRATEGY_REGISTRY.create("grid", symbols=["BTC/USDT"])
    res = run_backtest(grid, {"BTC/USDT": _wave()}, start_cash=10_000.0)
    assert res.final_equity > 0
    assert 0.0 <= res.win_rate <= 1.0
    assert res.montecarlo is not None
    d = res.as_dict()
    assert "montecarlo" in d
