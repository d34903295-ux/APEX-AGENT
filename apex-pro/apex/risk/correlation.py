"""Rolling correlation tracker for portfolio-level risk.

Tracks per-symbol return series and computes Pearson correlation over the
overlapping window (pure python, no numpy needed). The risk-manager uses it to
cap aggregate exposure to a cluster of correlated assets — so the agent can't
quietly take one big bet dressed up as five "different" positions.
"""
from __future__ import annotations

from collections import defaultdict, deque
from statistics import fmean, pstdev


class CorrelationTracker:
    def __init__(self, window: int = 100):
        self.window = window
        self._rets: dict[str, deque] = defaultdict(lambda: deque(maxlen=window))
        self._last: dict[str, float] = {}

    def update(self, symbol: str, price: float) -> None:
        last = self._last.get(symbol)
        if last and last > 0:
            self._rets[symbol].append(price / last - 1.0)
        self._last[symbol] = price

    def correlation(self, a: str, b: str) -> float:
        if a == b:
            return 1.0
        ra, rb = self._rets.get(a), self._rets.get(b)
        if not ra or not rb:
            return 0.0
        n = min(len(ra), len(rb))
        if n < 20:
            return 0.0
        xa = list(ra)[-n:]
        xb = list(rb)[-n:]
        ma, mb = fmean(xa), fmean(xb)
        sa, sb = pstdev(xa), pstdev(xb)
        if sa == 0 or sb == 0:
            return 0.0
        cov = fmean([(x - ma) * (y - mb) for x, y in zip(xa, xb)])
        return max(-1.0, min(1.0, cov / (sa * sb)))

    def correlated_symbols(self, symbol: str, candidates, threshold: float = 0.7) -> list[str]:
        """Symbols that *co-move* with `symbol` (positive correlation).

        We use signed correlation, not abs: inversely-correlated assets hedge
        each other and should NOT be lumped into the same concentration cluster.
        """
        return [c for c in candidates
                if c != symbol and self.correlation(symbol, c) >= threshold]
