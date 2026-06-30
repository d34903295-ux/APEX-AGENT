"""Automated yield farming — APY/risk-aware capital rotation.

Consumes 'defi_yields' items (from the on-chain source: Aave, Compound, Curve,
Convex, Lido, etc.) and rotates idle stablecoins toward the best
risk-adjusted APY among *audited* protocols. Risk score gates everything: a
20% APY on an unaudited fork is worth less than 6% on Aave.

Execution (approve + deposit/withdraw) is delegated to the execution-gateway's
DeFi adapters. This emits intent only.
"""
from __future__ import annotations

from apex.core.models import MarketTick, Signal, Side, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy

# Curated allow-list of audited protocols and a static risk score (0..1, 1=safe).
PROTOCOL_RISK = {
    "aave-v3": 0.95, "compound-v3": 0.92, "lido": 0.9, "curve": 0.85,
    "convex": 0.8, "yearn": 0.8, "morpho": 0.82,
}


@STRATEGY_REGISTRY.register("yield")
class YieldFarmingStrategy(Strategy):
    name = "yield"

    def __init__(self, symbols=None, min_apy: float = 0.04, min_risk: float = 0.8,
                 rotate_threshold: float = 0.01, **params):
        super().__init__(symbols, **params)
        self.min_apy = min_apy
        self.min_risk = min_risk
        self.rotate_threshold = rotate_threshold
        self._current: dict[str, str] = {}  # asset -> protocol

    def on_news(self, item: dict) -> list[Signal]:
        if item.get("type") != "defi_yields":
            return []
        asset = item.get("asset", "USDC")
        pools = item.get("pools", [])  # [{protocol, apy, chain, tvl_usd}, ...]
        best = None
        for p in pools:
            risk = PROTOCOL_RISK.get(p.get("protocol", ""), 0.0)
            if risk < self.min_risk or p.get("apy", 0) < self.min_apy:
                continue
            radj = p["apy"] * risk
            if best is None or radj > best[0]:
                best = (radj, p)
        if not best:
            return []

        _, pool = best
        return [self._signal(
            symbol=asset, side=Side.BUY, action=SignalAction.REBALANCE,
            confidence=PROTOCOL_RISK.get(pool["protocol"], 0.5), target_pct=1.0,
            exchange=pool.get("protocol"),
            rationale=f"farm {asset} -> {pool['protocol']} APY={pool['apy']:.2%}",
            meta={"defi": True, "chain": pool.get("chain"), **pool},
        )]

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        return []
