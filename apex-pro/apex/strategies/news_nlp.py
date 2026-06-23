"""News / social sentiment strategy with pump-and-dump *defense*.

Consumes sentiment items from the NEWS channel (produced by the data-feeder's
sentiment sources: Twitter/X, Telegram callers, Reddit, news portals). It:

  * trades *with* strong, broad-based, credible sentiment shifts, and
  * actively AVOIDS coordinated pump-and-dump bursts.

NOTE ON ETHICS/LEGALITY: this strategy DETECTS pump-and-dump patterns in order
to stay away from them (and optionally to fade the inevitable dump). It does
NOT originate or amplify them — orchestrating a pump is market manipulation
and is illegal. The anomaly detector's output is used as a *risk veto*.
"""
from __future__ import annotations

from collections import defaultdict, deque

from apex.core.models import MarketTick, Side, Signal, SignalAction
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies.base import Strategy


class _MentionAnomaly:
    """Detects abnormal spikes in mention volume (a P&D fingerprint)."""

    def __init__(self, window: int = 200):
        self.counts: dict[str, deque] = defaultdict(lambda: deque(maxlen=window))

    def update(self, symbol: str, mentions: int) -> float:
        d = self.counts[symbol]
        d.append(mentions)
        if len(d) < 20:
            return 0.0
        baseline = sum(d) / len(d)
        if baseline <= 0:
            return 0.0
        return mentions / baseline  # z-ish ratio; >5 == suspicious spike


@STRATEGY_REGISTRY.register("news")
class NewsSentimentStrategy(Strategy):
    name = "news"

    def __init__(self, symbols=None, min_sentiment: float = 0.4,
                 pump_ratio_veto: float = 5.0, size_pct: float = 0.03, **params):
        super().__init__(symbols, **params)
        self.min_sentiment = min_sentiment
        self.pump_ratio_veto = pump_ratio_veto
        self.size_pct = size_pct
        self._anomaly = _MentionAnomaly()

    def on_news(self, item: dict) -> list[Signal]:
        if item.get("type") != "sentiment":
            return []
        symbol = item.get("symbol")
        if not symbol or (self.symbols and symbol not in self.symbols):
            return []

        sentiment = float(item.get("score", 0))     # -1..1
        sources = int(item.get("source_count", 1))  # breadth
        mentions = int(item.get("mentions", 0))
        ratio = self._anomaly.update(symbol, mentions)

        # VETO: classic pump signature (few sources, huge mention spike).
        if ratio >= self.pump_ratio_veto and sources < 5:
            return [self._signal(
                symbol=symbol, side=Side.SELL, action=SignalAction.CLOSE,
                confidence=0.8, rationale=f"P&D anomaly ratio={ratio:.1f}; risk-off",
                meta={"veto": True, "pump_ratio": ratio},
            )]

        if abs(sentiment) < self.min_sentiment or sources < 3:
            return []

        side = Side.BUY if sentiment > 0 else Side.SELL
        return [self._signal(
            symbol=symbol, side=side, action=SignalAction.OPEN,
            confidence=min(0.85, 0.5 + abs(sentiment)), target_pct=self.size_pct,
            rationale=f"sentiment={sentiment:+.2f} across {sources} sources",
        )]

    def on_tick(self, tick: MarketTick) -> list[Signal]:
        return []
