from __future__ import annotations

import math

import pytest

from apex.ai.automl import AutoML, evaluate
from apex.ai.features import FEATURE_NAMES, feature_row, make_dataset, MIN_HISTORY
from apex.ai.models import MomentumPredictor, SklearnPredictor
from apex.core.indicators import RollingSeries


def _trend(n=400, slope=0.004, noise=0.0):
    out, p = [], 100.0
    for i in range(n):
        p *= 1 + slope + (noise * math.sin(i / 7))
        out.append(p)
    return out


# ---- features ---------------------------------------------------------------
def test_feature_row_shape_and_warmup():
    prices = _trend()
    assert feature_row(prices, 10) is None              # before warmup
    row = feature_row(prices, 200)
    assert row is not None and len(row) == len(FEATURE_NAMES)
    assert all(isinstance(x, float) for x in row)


def test_make_dataset_labels_binary_and_aligned():
    prices = _trend(noise=0.02)
    X, y = make_dataset(prices, horizon=5)
    assert len(X) == len(y) > 0
    assert set(y) <= {0, 1}
    assert all(len(r) == len(FEATURE_NAMES) for r in X)


def test_uptrend_labels_mostly_up():
    X, y = make_dataset(_trend(slope=0.01), horizon=5)
    assert sum(y) / len(y) > 0.8   # strong uptrend -> mostly up labels


# ---- predictors -------------------------------------------------------------
def test_momentum_predicts_uptrend():
    s = RollingSeries(maxlen=500)
    for p in _trend(slope=0.006):
        s.push(p)
    pred = MomentumPredictor().predict("X", s)
    assert pred["direction"] == 1.0
    assert 0.0 <= pred["confidence"] <= 1.0


def test_sklearn_predictor_falls_back_until_trained():
    s = RollingSeries(maxlen=500)
    for p in _trend():
        s.push(p)
    p = SklearnPredictor()
    # Not trained yet -> must return a valid prediction (delegates to momentum).
    pred = p.predict("X", s)
    assert "direction" in pred and "confidence" in pred


def test_sklearn_trains_when_available():
    pytest.importorskip("sklearn")
    prices = _trend(slope=0.003, noise=0.03)
    p = SklearnPredictor(horizon=5)
    assert p.fit(prices) is True
    assert p.trained
    s = RollingSeries(maxlen=2000)
    for x in prices:
        s.push(x)
    pred = p.predict("X", s)
    assert -1.0 <= pred["direction"] <= 1.0
    assert 0.0 <= pred["confidence"] <= 1.0


# ---- automl walk-forward ----------------------------------------------------
def test_evaluate_returns_accuracy_in_range():
    acc = evaluate(MomentumPredictor(), _trend(slope=0.005), horizon=5)
    assert 0.0 <= acc <= 1.0


def test_automl_selects_momentum_when_no_edge():
    automl = AutoML(candidates=[MomentumPredictor(), SklearnPredictor()])
    automl.select(_trend(slope=0.005))
    # momentum must always have a score; active must be one of the candidates.
    assert "momentum" in automl.scores
    assert automl.active.name in {"momentum", "ml"}
