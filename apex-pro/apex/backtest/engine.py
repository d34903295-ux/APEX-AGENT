"""Backtester + forward-test gate.

Before a strategy is allowed to touch real capital, APEX:
  1. Backtests it on historical OHLCV (this engine).
  2. Forward-tests it in PAPER mode for 24h (orchestrator + PaperExecutor).
  3. Runs a Monte Carlo on the resulting trade distribution.
Only if Monte Carlo says `safe_to_go_live` does the risk-manager unlock it.

This engine replays a price series through a single strategy and a fresh
paper portfolio, returning performance stats.
"""
from __future__ import annotations

from dataclasses import dataclass

from apex.core.models import MarketTick
from apex.core.portfolio import Portfolio
from apex.execution.paper import PaperExecutor
from apex.risk.manager import RiskManager
from apex.risk.montecarlo import MonteCarloResult, simulate
from apex.strategies.base import Strategy


@dataclass
class BacktestResult:
    trades: int
    final_equity: float
    return_pct: float
    max_drawdown: float
    win_rate: float
    montecarlo: MonteCarloResult | None = None

    def as_dict(self) -> dict:
        d = self.__dict__.copy()
        d["montecarlo"] = self.montecarlo.as_dict() if self.montecarlo else None
        return d


def run_backtest(strategy: Strategy, prices: dict[str, list[float]],
                 start_cash: float = 10_000.0) -> BacktestResult:
    """Replay synchronous prices through strategy -> risk -> paper fills."""
    rm = RiskManager(portfolio=Portfolio(cash=start_cash))
    ex = PaperExecutor()
    equity_curve: list[float] = [start_cash]
    trade_returns: list[float] = []
    last_equity = start_cash

    n = max(len(v) for v in prices.values())
    for i in range(n):
        for sym, series in prices.items():
            if i >= len(series):
                continue
            px = series[i]
            ex.update_mark(sym, px)
            rm.pf.mark(sym, px)
            rm.on_tick_price(sym, px)
            for sig in strategy.on_tick(MarketTick(symbol=sym, price=px)):
                order, reason = rm.evaluate(sig)
                if not order:
                    continue
                fill = ex.execute(order)
                if fill:
                    rm.on_fill(fill)
        eq = rm.pf.total_equity()
        equity_curve.append(eq)
        if eq != last_equity:
            trade_returns.append((eq - last_equity) / last_equity)
            last_equity = eq

    peak = start_cash
    max_dd = 0.0
    for eq in equity_curve:
        peak = max(peak, eq)
        max_dd = max(max_dd, (peak - eq) / peak if peak else 0)

    wins = sum(1 for r in trade_returns if r > 0)
    win_rate = wins / len(trade_returns) if trade_returns else 0.0
    final = equity_curve[-1]

    mc = None
    if trade_returns:
        import statistics
        mean = statistics.fmean(trade_returns)
        std = statistics.pstdev(trade_returns) or 1e-6
        mc = simulate(mean, std, win_rate=win_rate, paths=2000, horizon=len(trade_returns) or 50)

    return BacktestResult(
        trades=len(trade_returns), final_equity=final,
        return_pct=(final - start_cash) / start_cash, max_drawdown=max_dd,
        win_rate=win_rate, montecarlo=mc,
    )
