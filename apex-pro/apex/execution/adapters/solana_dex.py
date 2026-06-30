"""Solana DEX adapter (Jupiter aggregator) — scaffold.

Jupiter is the natural router for Solana. Implementation outline:
  1. GET https://quote-api.jup.ag/v6/quote  (inputMint, outputMint, amount, slippageBps)
  2. POST https://quote-api.jup.ag/v6/swap   with the quote + your pubkey
  3. sign the returned transaction with SOLANA_PRIVATE_KEY (hot wallet) via solders
  4. send + confirm; parse balances delta -> Fill
Inert until SOLANA_RPC_URL + key are provided and steps are completed.
"""
from __future__ import annotations

from apex.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.core.models import Fill, Order
from apex.execution.adapters.base import SOLANA_DEX_VENUES, ExchangeAdapter

log = get_logger("apex.exec.sol")


class SolanaDexAdapter(ExchangeAdapter):
    venue_type = "solana_dex"

    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()

    def supports(self, venue: str) -> bool:
        return (venue or "").lower() in SOLANA_DEX_VENUES

    def execute(self, order: Order) -> Fill | None:
        log.info("Solana DEX swap requested (%s) — adapter not yet wired; skipping",
                 order.exchange)
        return None
