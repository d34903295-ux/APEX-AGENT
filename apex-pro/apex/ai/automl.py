"""AutoML: walk-forward model selection.

Each candidate is trained on the in-sample window and scored on the held-out
out-of-sample window by directional accuracy. The best OOS scorer becomes the
active predictor. This is the weekly-cadence selection the spec asks for —
call `select(prices)` on a schedule with recent data.

Walk-forward (not random CV) because market data is sequential: training on the
future to predict the past leaks information and overstates accuracy.
"""
from __future__ import annotations

from apex.ai.base import Predictor
from apex.ai.features import MIN_HISTORY
from apex.ai.models import MomentumPredictor, SklearnPredictor
from apex.core.indicators import RollingSeries
from apex.core.logging import get_logger

log = get_logger("apex.ai.automl")


def evaluate(predictor: Predictor, prices: list[float], *,
             train_frac: float = 0.7, horizon: int = 5) -> float:
    """Out-of-sample directional accuracy in [0,1] (0.5 == coin flip)."""
    n = len(prices)
    if n < MIN_HISTORY + 2 * horizon + 20:
        return 0.0
    split = max(MIN_HISTORY + 10, int(n * train_frac))
    predictor.fit(prices[:split])

    correct = total = 0
    s = RollingSeries(maxlen=n + 1)
    for p in prices[:split]:
        s.push(p)
    for i in range(split, n - horizon):
        s.push(prices[i])
        pred = predictor.predict("eval", s)
        if pred["confidence"] <= 0:
            continue
        fwd = prices[i + horizon] / prices[i] - 1.0 if prices[i] else 0.0
        label = 1.0 if fwd > 0 else -1.0
        correct += int(pred["direction"] == label)
        total += 1
    return correct / total if total else 0.0


class AutoML:
    def __init__(self, candidates: list[Predictor] | None = None):
        self.candidates = candidates or [MomentumPredictor(), SklearnPredictor()]
        self.active: Predictor = self.candidates[0]
        self.scores: dict[str, float] = {}

    def select(self, prices: list[float]) -> Predictor:
        """Score every candidate walk-forward and activate the best."""
        self.scores = {}
        for cand in self.candidates:
            try:
                self.scores[cand.name] = evaluate(cand, prices)
            except Exception as exc:  # pragma: no cover
                log.warning("evaluate %s failed: %s", cand.name, exc)
                self.scores[cand.name] = 0.0
        if self.scores:
            best = max(self.scores, key=self.scores.get)
            # Only switch away from the baseline if a model genuinely beats it.
            if self.scores[best] > self.scores.get("momentum", 0) + 0.01:
                self.active = next(c for c in self.candidates if c.name == best)
            else:
                self.active = next(c for c in self.candidates if c.name == "momentum")
        log.info("AutoML scores=%s -> active=%s",
                 {k: round(v, 3) for k, v in self.scores.items()}, self.active.name)
        return self.active
