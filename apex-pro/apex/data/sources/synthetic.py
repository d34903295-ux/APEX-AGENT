"""Synthetic market data source — geometric brownian motion.

Lets the whole agent run end-to-end with ZERO external dependencies or API
keys. Perfect for demos, CI and developing strategies offline.
"""
from __future__ import annotations

import asyncio
import random
from collections.abc import AsyncIterator

from apex.core.models import MarketTick


class SyntheticSource:
    name = "synthetic"

    def __init__(self, symbols: list[str], start_prices: dict[str, float] | None = None,
                 vol: float = 0.002, interval: float = 0.5, seed: int | None = None):
        self.symbols = symbols
        self.vol = vol
        self.interval = interval
        self.rng = random.Random(seed)
        self.prices = {s: (start_prices or {}).get(s, 100.0 * (i + 1))
                       for i, s in enumerate(symbols)}

    async def stream(self) -> AsyncIterator[MarketTick]:
        while True:
            for sym in self.symbols:
                drift = self.rng.gauss(0, self.vol)
                self.prices[sym] = max(0.01, self.prices[sym] * (1 + drift))
                px = self.prices[sym]
                spread = px * 0.0004
                yield MarketTick(
                    symbol=sym, price=px, bid=px - spread / 2, ask=px + spread / 2,
                    volume=self.rng.uniform(1, 100), exchange="synthetic",
                )
            await asyncio.sleep(self.interval)
