"""Low-latency L2 order-book source via ccxt.pro websockets.

Yields MarketTicks enriched with L2 depth in `meta` (`bids`/`asks`), which the
scalping strategy uses to compute order-book imbalance (OBI). Falls back
cleanly if ccxt.pro is unavailable.

ccxt unified websockets ship as `ccxt.pro` in modern ccxt versions:
    import ccxt.pro as ccxtpro
"""
from __future__ import annotations

import asyncio
from collections.abc import AsyncIterator

from apex.core.logging import get_logger
from apex.core.models import MarketTick

log = get_logger("apex.data.ws")


class OrderBookWSSource:
    name = "orderbook_ws"

    def __init__(self, exchange: str, symbols: list[str], depth: int = 20,
                 credentials: dict | None = None):
        try:
            import ccxt.pro as ccxtpro  # type: ignore
        except Exception as exc:  # pragma: no cover - optional dep
            raise RuntimeError(f"ccxt.pro unavailable: {exc}")
        klass = getattr(ccxtpro, exchange)
        self.client = klass({**(credentials or {}), "enableRateLimit": True})
        self.exchange_name = exchange
        self.symbols = symbols
        self.depth = depth

    async def _watch_symbol(self, symbol: str, queue: asyncio.Queue) -> None:
        while True:
            try:  # pragma: no cover - network
                ob = await self.client.watch_order_book(symbol, self.depth)
                bids = ob.get("bids", [])[: self.depth]
                asks = ob.get("asks", [])[: self.depth]
                bid = bids[0][0] if bids else 0.0
                ask = asks[0][0] if asks else 0.0
                mid = (bid + ask) / 2 if bid and ask else (bid or ask)
                await queue.put(MarketTick(
                    symbol=symbol, price=mid, bid=bid, ask=ask,
                    exchange=self.exchange_name,
                    meta={"bids": bids, "asks": asks},
                ))
            except Exception as exc:
                log.warning("watch_order_book %s failed: %s; backing off", symbol, exc)
                await asyncio.sleep(2)

    async def stream(self) -> AsyncIterator[MarketTick]:
        queue: asyncio.Queue = asyncio.Queue(maxsize=1000)
        for sym in self.symbols:
            asyncio.create_task(self._watch_symbol(sym, queue))
        while True:
            yield await queue.get()
