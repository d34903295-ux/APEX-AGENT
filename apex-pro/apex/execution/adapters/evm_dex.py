"""EVM DEX adapter (Uniswap-style routers) — scaffold.

A safe, structured place to wire real on-chain swaps with web3.py. It is
deliberately INERT until you complete the marked steps and provide an RPC +
hot-wallet key. Until then it returns None (gateway falls back / drops).

Implementation outline (do NOT skip the safety steps):
  1. load web3, connect to <chain>_RPC_URL, load EVM_PRIVATE_KEY (hot wallet)
  2. resolve router (Uniswap V3 SwapRouter / Universal Router) + token decimals
  3. SIMULATE the swap (eth_call) and compute expected out + price impact
  4. enforce slippage + min-out; build tx with a deadline; sign; send
  5. wait for receipt; parse the actual amounts -> Fill
  6. ALWAYS pair sniper buys with the honeypot screen (sell-simulation) first
"""
from __future__ import annotations

from apex.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.core.models import Fill, Order
from apex.execution.adapters.base import EVM_DEX_VENUES, ExchangeAdapter

log = get_logger("apex.exec.evm")

RPC_ENV = {
    "ethereum": "ETH_RPC_URL", "bsc": "BSC_RPC_URL",
    "polygon": "POLYGON_RPC_URL", "arbitrum": "ARBITRUM_RPC_URL",
}


class EvmDexAdapter(ExchangeAdapter):
    venue_type = "evm_dex"

    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()

    def supports(self, venue: str) -> bool:
        return (venue or "").lower() in EVM_DEX_VENUES

    def execute(self, order: Order) -> Fill | None:
        # INERT scaffold: refuse to fabricate a fill. Wire web3 per the outline.
        log.info("EVM DEX swap requested (%s) — adapter not yet wired; skipping",
                 order.exchange)
        return None
