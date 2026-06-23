"""On-chain MEV — LEGITIMATE strategies only.

================================ READ THIS =================================
APEX deliberately implements only *non-predatory* MEV:

  * BACKRUN ARBITRAGE  — after someone moves a pool, restore the price across
    venues and capture the spread. Harms no one; improves market efficiency.
  * LIQUIDATIONS       — repay undercollateralised loans for the protocol
    bonus. A public, intended protocol mechanism.

We do NOT implement sandwich attacks or victim front-running. Those extract
value directly from other users' trades, are widely considered abusive, are
illegal as market manipulation in several jurisdictions, and are exactly the
behaviour flashbots/MEV-protect were built to stop. The interface below has
NO hook for them by design.
===========================================================================

Execution requires a mempool stream + bundle submission (Flashbots/Jito) wired
in the execution-gateway. This module only *detects* and emits signals, and
must be paired with the local-fork simulator before any bundle is sent.
"""
from __future__ import annotations

from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy


@STRATEGY_REGISTRY.register("mev")
class BackrunArbitrageMEV(Strategy):
    name = "mev"

    def __init__(self, symbols=None, min_profit_usd: float = 25.0, **params):
        super().__init__(symbols, **params)
        self.min_profit_usd = min_profit_usd

    def on_news(self, item: dict) -> list[Signal]:
        """The data-feeder publishes 'pending_swap' / 'pool_update' events.

        STUB: emit a backrun-arb signal when a detectable cross-venue price
        dislocation appears *after* a confirmed swap. Always simulate on a fork
        before the execution-gateway submits a bundle.
        """
        if item.get("type") != "pool_dislocation":
            return []
        est_profit = float(item.get("est_profit_usd", 0))
        if est_profit < self.min_profit_usd:
            return []
        return [self._signal(
            symbol=item.get("symbol", "?"), side=Side.BUY, action=SignalAction.OPEN,
            confidence=0.7, target_pct=0.02, exchange=item.get("dex", "uniswap"),
            rationale=f"backrun-arb est_profit=${est_profit:.0f} (simulate before send)",
            meta={"mev_type": "backrun_arb", "requires_fork_sim": True, **item},
        )]

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        return []
