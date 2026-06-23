"""Strategy-engine: runs enabled strategies and emits signals.

Subscribes to TICKS / NEWS / PREDICTIONS, fans each event out to every enabled
strategy, and publishes the resulting Signals. Strategies can be enabled or
disabled at runtime via the COMMANDS channel (/set_strategy from Telegram) —
this is the "plug-and-play en caliente" requirement.
"""
from __future__ import annotations

import asyncio

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.logging import get_logger
from apex.core.models import MarketTick
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies import available_strategies  # noqa: F401  (populates registry)

log = get_logger("apex.engine")

# Default roster per the conservative profile. Telegram can change this live.
DEFAULT_ENABLED = ["grid", "dca"]


class StrategyEngine:
    def __init__(self, symbols: list[str], enabled: list[str] | None = None):
        self.symbols = symbols
        self.strategies = {}
        for name in (enabled or DEFAULT_ENABLED):
            self.enable(name)

    def enable(self, name: str, **params) -> bool:
        try:
            strat = STRATEGY_REGISTRY.create(name, symbols=self.symbols, **params)
        except KeyError:
            log.warning("enable: unknown strategy %s", name)
            return False
        self.strategies[name] = strat
        log.info("[green]strategy enabled[/green]: %s", name)
        return True

    def disable(self, name: str) -> bool:
        if name in self.strategies:
            del self.strategies[name]
            log.info("[yellow]strategy disabled[/yellow]: %s", name)
            return True
        return False

    def _collect(self, method: str, payload) -> list:
        signals = []
        for strat in list(self.strategies.values()):
            if not strat.enabled:
                continue
            try:
                signals.extend(getattr(strat, method)(payload))
            except Exception as exc:  # pragma: no cover - strategy bug isolation
                log.error("strategy %s.%s error: %s", strat.name, method, exc)
        return signals

    async def run(self) -> None:
        bus = await make_bus()
        log.info("Strategy-engine running: %s", list(self.strategies))

        async def pump(channel: str, method: str, decode):
            async for msg in bus.subscribe(channel):
                payload = decode(msg)
                for sig in self._collect(method, payload):
                    await bus.publish(Channels.SIGNALS, sig.to_dict())

        async def commands():
            async for cmd in bus.subscribe(Channels.COMMANDS):
                self._handle_command(cmd)

        await asyncio.gather(
            pump(Channels.TICKS, "on_tick", MarketTick.from_dict),
            pump(Channels.NEWS, "on_news", lambda m: m),
            pump(Channels.PREDICTIONS, "on_prediction", lambda m: m),
            commands(),
        )

    def _handle_command(self, cmd: dict) -> None:
        action = cmd.get("action")
        if action == "enable_strategy":
            self.enable(cmd["name"], **cmd.get("params", {}))
        elif action == "disable_strategy":
            self.disable(cmd["name"])


async def run(symbols: list[str], enabled: list[str] | None = None) -> None:
    await StrategyEngine(symbols, enabled).run()
