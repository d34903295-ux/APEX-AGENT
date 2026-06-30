"""Monte Carlo simulation for drawdown / risk-of-ruin estimation.

Used by the backtester and the "should we go live?" gate. Given a strategy's
per-trade return distribution (mean, std, win rate), it simulates thousands of
equity paths and reports the distribution of max drawdowns and the probability
of ruin. If risk-of-ruin is non-trivial, APEX refuses to allocate real capital.
"""
from __future__ import annotations

import random
from dataclasses import dataclass


@dataclass
class MonteCarloResult:
    paths: int
    horizon: int
    median_return: float
    p5_return: float
    p95_return: float
    median_max_drawdown: float
    worst_max_drawdown: float
    prob_ruin: float

    def as_dict(self) -> dict:
        return self.__dict__.copy()

    @property
    def safe_to_go_live(self) -> bool:
        """A conservative gate: low ruin probability and bounded drawdowns."""
        return self.prob_ruin < 0.01 and self.median_max_drawdown < 0.35


def simulate(
    mean_return: float,
    std_return: float,
    *,
    win_rate: float | None = None,
    paths: int = 5_000,
    horizon: int = 250,
    ruin_threshold: float = 0.5,
    seed: int | None = None,
) -> MonteCarloResult:
    """Simulate `paths` equity curves of `horizon` trades.

    mean_return / std_return are per-trade simple returns on equity.
    ruin = equity drops below (1 - ruin_threshold) of the start at any point.
    """
    rng = random.Random(seed)
    finals: list[float] = []
    max_dds: list[float] = []
    ruined = 0

    for _ in range(paths):
        equity = 1.0
        peak = 1.0
        max_dd = 0.0
        is_ruined = False
        for _ in range(horizon):
            r = rng.gauss(mean_return, std_return)
            equity *= (1 + r)
            if equity <= 0:
                equity = 1e-9
            peak = max(peak, equity)
            dd = (peak - equity) / peak
            max_dd = max(max_dd, dd)
            if equity < (1 - ruin_threshold):
                is_ruined = True
        finals.append(equity - 1.0)
        max_dds.append(max_dd)
        ruined += int(is_ruined)

    finals.sort()
    max_dds.sort()

    def pct(arr, p):
        return arr[min(len(arr) - 1, int(len(arr) * p))]

    return MonteCarloResult(
        paths=paths,
        horizon=horizon,
        median_return=pct(finals, 0.5),
        p5_return=pct(finals, 0.05),
        p95_return=pct(finals, 0.95),
        median_max_drawdown=pct(max_dds, 0.5),
        worst_max_drawdown=max_dds[-1],
        prob_ruin=ruined / paths,
    )
