"""Live CEX market-data source via ccxt (REST polling; swap to ws for prod).

Polls tickers for the configured symbols on one exchange and yields normalised
MarketTicks. For production-grade latency, replace the poll loop with ccxt.pro
websockets — the rest of the pipeline is identical.
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from apex.core.logging import get_logger
from apex.core.models import MarketTick

log = get_logger("apex.data.ccxt")


class CCXTSource:
    name = "ccxt"

    def __init__(self, exchange: str, symbols: list[str], interval: float = 1.0,
                 credentials: dict | None = None):
        import ccxt  # lazy import

        klass = getattr(ccxt, exchange)
        self.exchange_name = exchange
        self.client = klass({**(credentials or {}), "enableRateLimit": True})
        self.symbols = symbols
        self.interval = interval

    async def stream(self) -> AsyncIterator[MarketTick]:
        loop = asyncio.get_event_loop()
        while True:
            for sym in self.symbols:
                try:
                    t = await loop.run_in_executor(None, self.client.fetch_ticker, sym)
                    yield MarketTick(
                        symbol=sym, price=float(t["last"]),
                        bid=float(t.get("bid") or 0), ask=float(t.get("ask") or 0),
                        volume=float(t.get("baseVolume") or 0),
                        exchange=self.exchange_name,
                    )
                except Exception as exc:  # pragma: no cover - network
                    log.warning("fetch_ticker %s failed: %s", sym, exc)
            await asyncio.sleep(self.interval)
