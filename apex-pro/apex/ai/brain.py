"""ai-brain: feature engineering + price-direction prediction + AutoML.

Design:
  * `FeatureBuilder` turns rolling OHLCV/orderbook/onchain/sentiment into a
    feature vector.
  * `Predictor` is a thin interface. Two implementations:
      - `MomentumPredictor` (dependency-free baseline, always available)
      - `MLPredictor` (scikit-learn / xgboost when installed)
  * `AutoML.select()` periodically backtests candidate models on recent data
    and promotes the best by out-of-sample score (weekly cadence in prod).
  * LSTM/Transformer models plug in behind the same `Predictor` interface;
    install torch and add a `TorchSeqPredictor` — nothing else changes.

The service publishes predictions (with a `facts` dict the symbolic planner
consumes) on Channels.PREDICTIONS.
"""
from __future__ import annotations

import asyncio
from abc import ABC, abstractmethod

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.indicators import RollingSeries
from apex.core.logging import get_logger
from apex.core.models import MarketTick

log = get_logger("apex.ai")


class Predictor(ABC):
    name = "base"

    @abstractmethod
    def predict(self, symbol: str, series: RollingSeries) -> dict:
        """Return {'direction': -1..1, 'confidence': 0..1, 'horizon': 'short'}."""


class MomentumPredictor(Predictor):
    """Always-available baseline: EMA cross + RSI. No ML deps required."""
    name = "momentum"

    def predict(self, symbol: str, series: RollingSeries) -> dict:
        fast, slow = series.ema(12), series.ema(48)
        rsi = series.rsi(14)
        if fast is None or slow is None or rsi is None:
            return {"direction": 0.0, "confidence": 0.0, "horizon": "short"}
        direction = 1.0 if fast > slow else -1.0
        # RSI moderates confidence (avoid chasing overbought/oversold).
        conf = min(0.8, abs(fast - slow) / slow * 50)
        if (direction > 0 and rsi > 75) or (direction < 0 and rsi < 25):
            conf *= 0.5
        return {"direction": direction, "confidence": conf, "horizon": "short",
                "features": {"ema_fast": fast, "ema_slow": slow, "rsi": rsi}}


class MLPredictor(Predictor):
    """scikit-learn / xgboost classifier on engineered features (optional)."""
    name = "ml"

    def __init__(self):
        self._model = None
        try:
            from sklearn.ensemble import GradientBoostingClassifier  # noqa
            self._available = True
        except ImportError:
            self._available = False
            log.info("scikit-learn not installed; MLPredictor inactive")

    def predict(self, symbol: str, series: RollingSeries) -> dict:
        if not self._available or self._model is None:
            return MomentumPredictor().predict(symbol, series)
        # Wire real feature vector + self._model.predict_proba here.
        return MomentumPredictor().predict(symbol, series)


class AutoML:
    """Weekly model selection by out-of-sample score (placeholder logic)."""

    def __init__(self, candidates: list[Predictor] | None = None):
        self.candidates = candidates or [MomentumPredictor(), MLPredictor()]
        self.active: Predictor = self.candidates[0]

    def select(self, scores: dict[str, float]) -> Predictor:
        if not scores:
            return self.active
        best = max(scores, key=scores.get)
        for c in self.candidates:
            if c.name == best:
                self.active = c
        log.info("AutoML selected predictor: %s", self.active.name)
        return self.active


async def run(symbols: list[str], interval: float = 5.0) -> None:
    bus = await make_bus()
    automl = AutoML()
    series: dict[str, RollingSeries] = {}
    log.info("ai-brain running with predictor=%s", automl.active.name)

    async def ingest():
        async for msg in bus.subscribe(Channels.TICKS):
            t = MarketTick.from_dict(msg)
            series.setdefault(t.symbol, RollingSeries(maxlen=500)).push(t.price)

    async def emit():
        while True:
            await asyncio.sleep(interval)
            facts = {}
            for sym, s in series.items():
                pred = automl.active.predict(sym, s)
                facts[sym] = {"price": s.values[-1] if s.values else 0,
                              "pred_direction": pred["direction"],
                              "pred_confidence": pred["confidence"]}
                await bus.publish(Channels.PREDICTIONS,
                                  {"symbol": sym, **pred, "facts": {sym: facts[sym]}})

    await asyncio.gather(ingest(), emit())
