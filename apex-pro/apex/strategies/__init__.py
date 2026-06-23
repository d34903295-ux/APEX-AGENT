"""Importing this package auto-registers every built-in strategy.

The strategy-engine then instantiates them by name from config, so you can
enable/disable strategies "in caliente" without touching code.
"""
from __future__ import annotations

from apex.core.registry import STRATEGY_REGISTRY

# Import for side effects (registration). Keep alphabetical.
from apex.strategies import (  # noqa: F401,E402
    arbitrage,
    dca,
    grid,
    mev,
    news_nlp,
    onchain_flow,
    planner,
    portfolio,
    scalping,
    sniper,
    yield_farming,
)


def available_strategies() -> list[str]:
    return STRATEGY_REGISTRY.available()


__all__ = ["STRATEGY_REGISTRY", "available_strategies"]
