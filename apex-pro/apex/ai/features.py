"""Feature engineering for the AI brain (pure-python, dependency-free).

Turns a price history into feature vectors + direction labels for supervised
learning. The same `feature_row` is used at train time and inference time, so
there's no train/serve skew.

Features (all scale-free so models transfer across assets):
  * multi-horizon returns (1, 3, 5, 10)
  * EMA(fast)/EMA(slow) ratio - 1
  * price / SMA(n) - 1  (distance from mean)
  * RSI(14) scaled to [-1, 1]
  * rolling return volatility
  * short momentum (price / price[-k] - 1)
"""
from __future__ import annotations

from apex.core.indicators import RollingSeries

FEATURE_NAMES = [
    "ret_1", "ret_3", "ret_5", "ret_10",
    "ema_ratio", "dist_sma20", "rsi_scaled", "volatility", "momentum_5",
]
MIN_HISTORY = 60  # need enough points for the slowest indicator


def _ret(prices: list[float], i: int, k: int) -> float:
    if i - k < 0 or prices[i - k] == 0:
        return 0.0
    return prices[i] / prices[i - k] - 1.0


def feature_row(prices: list[float], i: int) -> list[float] | None:
    """Compute the feature vector at index i (using only data up to i)."""
    if i < MIN_HISTORY:
        return None
    window = prices[: i + 1]
    s = RollingSeries(maxlen=len(window) + 1)
    for p in window:
        s.push(p)

    ema_fast, ema_slow = s.ema(12), s.ema(48)
    sma20 = s.sma(20)
    rsi = s.rsi(14)
    vol = s.returns_volatility(20)
    if None in (ema_fast, ema_slow, sma20, rsi, vol) or ema_slow == 0 or sma20 == 0:
        return None

    return [
        _ret(prices, i, 1), _ret(prices, i, 3), _ret(prices, i, 5), _ret(prices, i, 10),
        ema_fast / ema_slow - 1.0,
        prices[i] / sma20 - 1.0,
        (rsi - 50.0) / 50.0,
        vol,
        _ret(prices, i, 5),
    ]


def make_dataset(prices: list[float], horizon: int = 5,
                 deadband: float = 0.0) -> tuple[list[list[float]], list[int]]:
    """Build (X, y) where y = sign of the forward `horizon`-step return.

    deadband ignores tiny moves (label only strong up/down) when > 0.
    """
    X: list[list[float]] = []
    y: list[int] = []
    n = len(prices)
    for i in range(MIN_HISTORY, n - horizon):
        row = feature_row(prices, i)
        if row is None:
            continue
        fwd = prices[i + horizon] / prices[i] - 1.0 if prices[i] else 0.0
        if abs(fwd) < deadband:
            continue
        X.append(row)
        y.append(1 if fwd > 0 else 0)
    return X, y
