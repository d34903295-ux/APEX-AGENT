"""Data-feeder service: ingest market data and publish normalised ticks.

Auto-selects a source: a live ccxt source when an exchange + keys are available
and we're not forced to paper-only, otherwise the dependency-free synthetic
source. Publishes every tick on Channels.TICKS.

Extend by adding sources (sentiment, on-chain) that publish to Channels.NEWS —
the strategy-engine already routes NEWS items to strategy.on_news().
"""
from __future__ import annotations

import asyncio

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.config import get_settings
from apex.core.logging import get_logger
from apex.data.sources.synthetic import SyntheticSource

log = get_logger("apex.data.feeder")

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]


def build_source(symbols: list[str]):
    s = get_settings()
    # Try a live source only if creds exist for binance (most common).
    creds = s.exchange_credentials("binance")
    if creds.get("apiKey"):
        # Prefer low-latency L2 websockets (gives scalping real order-book OBI).
        try:
            from apex.data.sources.orderbook_ws import OrderBookWSSource

            log.info("Data-feeder: using L2 websocket source (binance, ccxt.pro)")
            return OrderBookWSSource("binance", symbols, credentials=creds)
        except Exception as exc:  # pragma: no cover
            log.warning("ccxt.pro unavailable (%s); trying REST", exc)
        try:
            from apex.data.sources.ccxt_source import CCXTSource

            log.info("Data-feeder: using live ccxt REST source (binance)")
            return CCXTSource("binance", symbols, credentials=creds)
        except Exception as exc:  # pragma: no cover
            log.warning("ccxt source unavailable (%s); using synthetic", exc)
    log.info("Data-feeder: using synthetic source (no live keys)")
    return SyntheticSource(symbols, start_prices={"BTC/USDT": 65000, "ETH/USDT": 3500, "SOL/USDT": 150})


async def run(symbols: list[str] | None = None) -> None:
    symbols = symbols or DEFAULT_SYMBOLS
    bus = await make_bus()
    source = build_source(symbols)
    log.info("Data-feeder streaming %s", symbols)
    async for tick in source.stream():
        await bus.publish(Channels.TICKS, tick.to_dict())


if __name__ == "__main__":
    asyncio.run(run())
