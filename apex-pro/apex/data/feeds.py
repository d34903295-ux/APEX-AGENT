"""Auxiliary data feeds -> NEWS channel (all using FREE/public endpoints).

Ships:
  * DeFi yields   (DefiLlama)          -> 'defi_yields'  (yield strategy)
  * Derivatives   (Binance public)     -> 'onchain'      (onchain_flow strategy)
  * New pools     (DexScreener public) -> 'new_pool'     (sniper + honeypot)

Each loop just publishes typed NEWS items; strategies already route NEWS to
their `on_news` handlers. Add sentiment crawlers here next (needs API tokens).
"""
from __future__ import annotations

import asyncio

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.logging import get_logger
from apex.data.feeder import DEFAULT_SYMBOLS
from apex.data.sources.defi_yields import fetch_yields
from apex.data.sources.derivatives import fetch_symbol_flow
from apex.data.sources.new_pools import fetch_new_pools

log = get_logger("apex.feeds")


async def yields_loop(interval: float = 1800.0) -> None:
    """Publish DeFi yields every 30 min."""
    bus = await make_bus()
    while True:
        pools_by_asset = fetch_yields()
        for asset, pools in pools_by_asset.items():
            if pools:
                await bus.publish(Channels.NEWS,
                                  {"type": "defi_yields", "asset": asset, "pools": pools})
        if pools_by_asset:
            log.info("published yields for %d assets", len(pools_by_asset))
        await asyncio.sleep(interval)


async def derivatives_loop(symbols: list[str], interval: float = 60.0) -> None:
    """Publish funding/OI/CVD flow per symbol every minute."""
    bus = await make_bus()
    loop = asyncio.get_event_loop()
    while True:
        for sym in symbols:
            item = await loop.run_in_executor(None, fetch_symbol_flow, sym)
            await bus.publish(Channels.NEWS, item)
        await asyncio.sleep(interval)


async def new_pools_loop(interval: float = 120.0, chains: set[str] | None = None) -> None:
    """Publish freshly-detected pools every 2 min (deduped by token address)."""
    bus = await make_bus()
    loop = asyncio.get_event_loop()
    seen: set[str] = set()
    while True:
        items = await loop.run_in_executor(None, lambda: fetch_new_pools(chains=chains))
        fresh = [it for it in items if it["token_address"] not in seen]
        for it in fresh:
            seen.add(it["token_address"])
            await bus.publish(Channels.NEWS, it)
        if fresh:
            log.info("detected %d new pools", len(fresh))
        # keep the dedup set bounded
        if len(seen) > 5000:
            seen = set(list(seen)[-2500:])
        await asyncio.sleep(interval)


async def run(symbols: list[str] | None = None) -> None:
    symbols = symbols or DEFAULT_SYMBOLS
    await asyncio.gather(
        yields_loop(),
        derivatives_loop(symbols),
        new_pools_loop(),
    )


if __name__ == "__main__":
    asyncio.run(run())
