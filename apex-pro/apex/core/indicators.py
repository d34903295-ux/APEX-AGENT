"""Pure-python technical indicators (no TA-Lib required).

Deliberately dependency-free so the core runs anywhere. If you install TA-Lib
or pandas-ta you can swap these out, but these are correct and fast enough for
real-time use on rolling windows.
"""
from __future__ import annotations

from collections import deque
from statistics import fmean, pstdev


class RollingSeries:
    """Fixed-size rolling window with O(1) appends and cheap indicators."""

    def __init__(self, maxlen: int = 500) -> None:
        self.values: deque[float] = deque(maxlen=maxlen)

    def push(self, v: float) -> None:
        self.values.append(float(v))

    def __len__(self) -> int:
        return len(self.values)

    def ready(self, n: int) -> bool:
        return len(self.values) >= n

    def sma(self, n: int) -> float | None:
        if len(self.values) < n:
            return None
        return fmean(list(self.values)[-n:])

    def ema(self, n: int) -> float | None:
        if len(self.values) < n:
            return None
        k = 2 / (n + 1)
        it = list(self.values)[-n:]
        ema = it[0]
        for v in it[1:]:
            ema = v * k + ema * (1 - k)
        return ema

    def stdev(self, n: int) -> float | None:
        if len(self.values) < n:
            return None
        return pstdev(list(self.values)[-n:])

    def rsi(self, n: int = 14) -> float | None:
        if len(self.values) < n + 1:
            return None
        vals = list(self.values)[-(n + 1):]
        gains, losses = 0.0, 0.0
        for a, b in zip(vals, vals[1:]):
            diff = b - a
            if diff >= 0:
                gains += diff
            else:
                losses -= diff
        if losses == 0:
            return 100.0
        rs = (gains / n) / (losses / n)
        return 100 - (100 / (1 + rs))

    def returns_volatility(self, n: int) -> float | None:
        """Std-dev of simple returns over the last n points (a volatility proxy)."""
        if len(self.values) < n + 1:
            return None
        vals = list(self.values)[-(n + 1):]
        rets = [(b - a) / a for a, b in zip(vals, vals[1:]) if a]
        if len(rets) < 2:
            return None
        return pstdev(rets)


def atr_from_prices(prices: list[float], n: int = 14) -> float | None:
    """Rough ATR proxy using close-to-close ranges when OHLC isn't available."""
    if len(prices) < n + 1:
        return None
    ranges = [abs(b - a) for a, b in zip(prices, prices[1:])]
    return fmean(ranges[-n:])
