"""Markowitz portfolio rebalancing with a Sharpe-maximising tilt.

Periodically computes target weights from the covariance of recent returns and
emits REBALANCE signals to move toward them. Uses a simple, dependency-light
mean-variance optimiser (closed-form for the max-Sharpe tangency portfolio,
long-only projected). For large universes swap in cvxpy.
"""
from __future__ import annotations

from apex.core.indicators import RollingSeries
from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy


@STRATEGY_REGISTRY.register("portfolio")
class MarkowitzRebalance(Strategy):
    name = "portfolio"

    def __init__(self, symbols=None, lookback: int = 100, rebalance_every: int = 500,
                 risk_free: float = 0.0, **params):
        super().__init__(symbols, **params)
        self.lookback = lookback
        self.rebalance_every = rebalance_every
        self.risk_free = risk_free
        self._series: dict[str, RollingSeries] = {}
        self._ticks = 0

    def _returns(self, sym: str) -> list[float]:
        vals = list(self._series[sym].values)[-(self.lookback + 1):]
        return [(b - a) / a for a, b in zip(vals, vals[1:]) if a]

    def _target_weights(self) -> dict[str, float]:
        import numpy as np

        syms = [s for s in self._series if self._series[s].ready(self.lookback)]
        if len(syms) < 2:
            return {}
        rets = np.array([self._returns(s) for s in syms])
        n = min(len(r) for r in self._returns_safe(syms))
        rets = np.array([self._returns(s)[-n:] for s in syms])
        mu = rets.mean(axis=1) - self.risk_free
        cov = np.cov(rets) + np.eye(len(syms)) * 1e-6
        try:
            w = np.linalg.solve(cov, mu)  # tangency portfolio (unconstrained)
        except np.linalg.LinAlgError:
            return {}
        w = np.clip(w, 0, None)           # long-only projection
        if w.sum() == 0:
            return {}
        w = w / w.sum()
        return dict(zip(syms, w.tolist()))

    def _returns_safe(self, syms):
        return [self._returns(s) for s in syms]

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        if self.symbols and tick.symbol not in self.symbols:
            return []
        self._series.setdefault(tick.symbol, RollingSeries(maxlen=self.lookback * 3)).push(tick.price)
        self._ticks += 1
        if self._ticks % self.rebalance_every != 0:
            return []
        try:
            weights = self._target_weights()
        except Exception:
            return []
        out = []
        for sym, w in weights.items():
            out.append(self._signal(
                symbol=sym, side=Side.BUY, action=SignalAction.REBALANCE,
                confidence=0.7, target_pct=w,
                rationale=f"Markowitz target weight {w:.2%}",
                meta={"rebalance": True},
            ))
        return out
