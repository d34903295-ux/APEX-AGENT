"""Position sizing via a *fractional* Kelly criterion.

Full Kelly is famously over-aggressive and assumes you know your edge exactly
(you don't). We use a fraction (default 0.25) and hard-cap by the risk profile.
"""
from __future__ import annotations


def kelly_fraction(win_prob: float, win_loss_ratio: float) -> float:
    """Classic Kelly: f* = p - (1-p)/b, clamped to [0, 1]."""
    if win_loss_ratio <= 0:
        return 0.0
    f = win_prob - (1 - win_prob) / win_loss_ratio
    return max(0.0, min(1.0, f))


def sized_position_pct(
    confidence: float,
    *,
    win_loss_ratio: float = 1.5,
    kelly_multiplier: float = 0.25,
    hard_cap: float = 0.10,
) -> float:
    """Translate a strategy's confidence (0..1) into a position size (% equity).

    confidence is treated as the estimated win probability. We apply fractional
    Kelly and then clamp to the profile's hard cap.
    """
    win_prob = max(0.0, min(0.99, confidence))
    f = kelly_fraction(win_prob, win_loss_ratio) * kelly_multiplier
    return max(0.0, min(hard_cap, f))
