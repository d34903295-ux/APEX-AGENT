"""DEX new-listing sniper with an integrated honeypot/rug filter.

The point of the filter is *capital protection*: most fresh tokens are scams.
We only emit a buy signal when a battery of safety checks passes. Execution on
a real DEX is delegated to the execution-gateway (web3/jupiter adapters).

SAFETY CHECKS (see `honeypot.py` for the actual probes):
  - sell simulation succeeds (token is sellable, not a honeypot)
  - buy/sell tax below a threshold
  - LP locked / burned, ownership renounced
  - liquidity above a floor, holder distribution not hyper-concentrated
"""
from __future__ import annotations

from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy
from apex.strategies.honeypot import HoneypotReport, screen_token


@STRATEGY_REGISTRY.register("sniper")
class DexSniperStrategy(Strategy):
    name = "sniper"

    def __init__(self, symbols=None, min_liquidity_usd: float = 25_000,
                 max_tax: float = 0.10, size_pct: float = 0.01, **params):
        super().__init__(symbols, **params)
        self.min_liquidity_usd = min_liquidity_usd
        self.max_tax = max_tax
        self.size_pct = size_pct

    def on_news(self, item: dict) -> list[Signal]:
        """The data-feeder publishes 'new_pool' events on the NEWS channel."""
        if item.get("type") != "new_pool":
            return []
        token = item.get("token_address")
        chain = item.get("chain", "ethereum")
        if not token:
            return []

        report: HoneypotReport = screen_token(
            token, chain, min_liquidity_usd=self.min_liquidity_usd, max_tax=self.max_tax
        )
        if not report.safe:
            return []  # protect capital: skip flagged tokens silently

        return [self._signal(
            symbol=item.get("symbol", token[:8]), side=Side.BUY,
            action=SignalAction.OPEN, confidence=report.score, target_pct=self.size_pct,
            exchange=item.get("dex", "uniswap"),
            stop_loss=None,  # set by risk-manager (ATR/trailing)
            rationale=f"sniper: passed honeypot screen score={report.score:.2f}",
            meta={"token": token, "chain": chain, "honeypot": report.as_dict()},
        )]

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        return []  # sniper is news/event driven, not tick driven
