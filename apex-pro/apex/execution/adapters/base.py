"""Execution adapters: one per venue type.

The gateway classifies an order's venue and routes to the right adapter:
  * CEX (binance, bybit, okx, kraken, ...) -> CCXTAdapter
  * EVM DEX (uniswap, pancakeswap, ...)    -> EvmDexAdapter
  * Solana DEX (jupiter, raydium, ...)     -> SolanaDexAdapter
Everything fails CLOSED: an adapter that can't safely fill returns None and the
gateway falls back to the paper executor (for non-live) or drops (for live).
"""
from __future__ import annotations

from abc import ABC, abstractmethod

from apex.core.models import Fill, Order


class ExchangeAdapter(ABC):
    venue_type: str = "base"

    @abstractmethod
    def supports(self, venue: str) -> bool: ...

    @abstractmethod
    def execute(self, order: Order) -> Fill | None: ...


# Venue classification tables (lowercase).
CEX_VENUES = {
    "binance", "binanceusdm", "bybit", "okx", "kraken", "coinbase",
    "kucoin", "gate", "gateio", "mexc", "htx", "bitget",
}
EVM_DEX_VENUES = {
    "uniswap", "uniswapv3", "pancakeswap", "sushiswap", "quickswap",
    "camelot", "1inch", "0x",
}
SOLANA_DEX_VENUES = {"jupiter", "raydium", "orca", "meteora"}


def classify_venue(venue: str) -> str:
    v = (venue or "").lower()
    if v in CEX_VENUES:
        return "cex"
    if v in EVM_DEX_VENUES:
        return "evm_dex"
    if v in SOLANA_DEX_VENUES:
        return "solana_dex"
    return "paper"
