"""Predictor interface shared by all models (baseline + ML).

Kept in its own module to avoid circular imports between brain/models/automl.
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from apex.core.indicators import RollingSeries


class Predictor(ABC):
    name: str = "base"
    trained: bool = False

    @abstractmethod
    def predict(self, symbol: str, series: RollingSeries) -> dict:
        """Return {'direction': -1..1, 'confidence': 0..1, 'horizon': str}."""

    def fit(self, prices: list[float]) -> bool:  # noqa: D401
        """Optionally train on a price history. Returns True if trained."""
        return False
