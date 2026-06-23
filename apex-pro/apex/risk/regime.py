"""Market regime / anomaly detector.

Watches realised volatility and price jumps per symbol. When volatility spikes
far beyond its recent baseline (a possible manipulation / flash-crash / news
shock), it flags an ABNORMAL regime so the risk-manager can auto-pause.
"""
from __future__ import annotations

from enum import Enum

from apex.core.indicators import RollingSeries


class Regime(str, Enum):
    CALM = "calm"
    NORMAL = "normal"
    VOLATILE = "volatile"
    ABNORMAL = "abnormal"   # triggers auto-pause


class RegimeDetector:
    def __init__(self, lookback: int = 100, jump_sigma: float = 6.0):
        self.lookback = lookback
        self.jump_sigma = jump_sigma
        self._series: dict[str, RollingSeries] = {}
        self._last: dict[str, float] = {}

    def update(self, symbol: str, price: float) -> Regime:
        s = self._series.setdefault(symbol, RollingSeries(maxlen=self.lookback * 3))
        last = self._last.get(symbol)
        s.push(price)
        self._last[symbol] = price

        vol = s.returns_volatility(self.lookback)
        if vol is None or vol == 0:
            return Regime.NORMAL

        # Single-tick jump in sigma units.
        if last:
            ret = abs((price - last) / last)
            if ret > self.jump_sigma * vol:
                return Regime.ABNORMAL

        if vol < 0.0008:
            return Regime.CALM
        if vol < 0.004:
            return Regime.NORMAL
        if vol < 0.012:
            return Regime.VOLATILE
        return Regime.ABNORMAL
