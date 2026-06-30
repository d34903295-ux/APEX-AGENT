"""Concrete predictors: a dependency-free baseline and a trainable ML model.

* MomentumPredictor — EMA cross + RSI. Always available, no training.
* SklearnPredictor  — GradientBoosting/XGBoost on engineered features. Trains
                      on a price history; falls back to momentum until trained
                      or if scikit-learn isn't installed.

Add an LSTM/Transformer by subclassing Predictor with the same `fit`/`predict`
contract — nothing else in the system changes.
"""
from __future__ import annotations

from apex.ai.base import Predictor
from apex.ai.features import feature_row, make_dataset
from apex.core.indicators import RollingSeries
from apex.core.logging import get_logger

log = get_logger("apex.ai.models")


class MomentumPredictor(Predictor):
    name = "momentum"
    trained = True  # nothing to train

    def predict(self, symbol: str, series: RollingSeries) -> dict:
        fast, slow = series.ema(12), series.ema(48)
        rsi = series.rsi(14)
        if fast is None or slow is None or rsi is None or slow == 0:
            return {"direction": 0.0, "confidence": 0.0, "horizon": "short"}
        direction = 1.0 if fast > slow else -1.0
        conf = min(0.8, abs(fast - slow) / slow * 50)
        if (direction > 0 and rsi > 75) or (direction < 0 and rsi < 25):
            conf *= 0.5
        return {"direction": direction, "confidence": conf, "horizon": "short"}


class SklearnPredictor(Predictor):
    name = "ml"

    def __init__(self, horizon: int = 5):
        self.horizon = horizon
        self._model = None
        self._fallback = MomentumPredictor()
        try:
            import sklearn  # noqa: F401
            self._available = True
        except ImportError:
            self._available = False

    def fit(self, prices: list[float]) -> bool:
        if not self._available:
            return False
        X, y = make_dataset(prices, horizon=self.horizon)
        if len(X) < 50 or len(set(y)) < 2:
            return False
        try:
            from sklearn.ensemble import GradientBoostingClassifier

            model = GradientBoostingClassifier(max_depth=3, n_estimators=120)
            model.fit(X, y)
            self._model = model
            self.trained = True
            return True
        except Exception as exc:  # pragma: no cover
            log.warning("SklearnPredictor.fit failed: %s", exc)
            return False

    def predict(self, symbol: str, series: RollingSeries) -> dict:
        if not self.trained or self._model is None:
            return self._fallback.predict(symbol, series)
        prices = list(series.values)
        row = feature_row(prices, len(prices) - 1)
        if row is None:
            return self._fallback.predict(symbol, series)
        try:
            proba = self._model.predict_proba([row])[0]  # [p_down, p_up]
            p_up = float(proba[1])
            direction = 1.0 if p_up >= 0.5 else -1.0
            confidence = abs(p_up - 0.5) * 2  # 0..1
            return {"direction": direction, "confidence": confidence,
                    "horizon": f"{self.horizon}-step", "p_up": p_up}
        except Exception as exc:  # pragma: no cover
            log.warning("predict failed: %s", exc)
            return self._fallback.predict(symbol, series)
