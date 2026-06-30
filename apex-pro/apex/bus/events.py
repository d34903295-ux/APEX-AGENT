"""Canonical channel names for the Redis Pub/Sub event bus."""
from __future__ import annotations


class Channels:
    TICKS = "apex.ticks"                # MarketTick (data-feeder -> everyone)
    SIGNALS = "apex.signals"            # Signal (strategy-engine -> risk-manager)
    ORDERS = "apex.orders"              # Order (risk-manager -> execution-gateway)
    FILLS = "apex.fills"               # Fill (execution-gateway -> everyone)
    RISK_EVENTS = "apex.risk"           # regime changes, pauses, rejections
    NEWS = "apex.news"                  # sentiment / news items
    COMMANDS = "apex.commands"          # telegram -> services (pause/resume/...)
    ALERTS = "apex.alerts"              # services -> telegram (proactive alerts)
    PREDICTIONS = "apex.predictions"    # ai-brain -> strategy-engine
    HEARTBEAT = "apex.heartbeat"        # liveness per service
