"""Strategy-engine: runs enabled strategies and emits signals.

Subscribes to TICKS / NEWS / PREDICTIONS, fans each event out to every enabled
strategy, and publishes the resulting Signals.

The active roster + per-strategy parameters + symbols come from a user-editable
`StrategyConfigStore` (JSON file). The user can change them three ways, all
without code:
  * edit data/strategy_config.json and restart, or
  * send Telegram commands (/set_strategy, /set_param, /symbols), which publish
    COMMANDS the engine applies live and persists.
"""
from __future__ import annotations

import asyncio

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.core.logging import get_logger
from apex.core.registry import STRATEGY_REGISTRY
from apex.strategies import available_strategies  # noqa: F401  (populates registry)
from apex.strategies.store import StrategyConfigStore

log = get_logger("apex.engine")


class StrategyEngine:
    def __init__(self, symbols: list[str] | None = None,
                 store: StrategyConfigStore | None = None,
                 enabled: list[str] | None = None):
        self.store = store or StrategyConfigStore().load(default_roster=enabled)
        if symbols:
            self.store.set_symbols(symbols)
        self.symbols = self.store.symbols
        self.strategies: dict = {}
        for name, params in self.store.enabled().items():
            self._instantiate(name, params)

    def _instantiate(self, name: str, params: dict | None = None) -> bool:
        try:
            strat = STRATEGY_REGISTRY.create(name, symbols=self.symbols, **(params or {}))
        except KeyError:
            log.warning("unknown strategy %s (available: %s)", name, STRATEGY_REGISTRY.available())
            return False
        except TypeError as exc:
            log.warning("bad params for %s: %s", name, exc)
            return False
        self.strategies[name] = strat
        return True

    # ---- user-facing controls (also reachable via Telegram COMMANDS) ----
    def enable(self, name: str, **params) -> bool:
        if not self._instantiate(name, params):
            return False
        self.store.enable(name, params)
        log.info("[green]strategy enabled[/green]: %s %s", name, params or "")
        return True

    def disable(self, name: str) -> bool:
        self.store.disable(name)
        if name in self.strategies:
            del self.strategies[name]
            log.info("[yellow]strategy disabled[/yellow]: %s", name)
            return True
        return False

    def set_param(self, name: str, key: str, value) -> bool:
        """Update a parameter and hot-rebuild the strategy with merged params."""
        params = self.store.set_param(name, key, value)
        if name in self.strategies and not self._instantiate(name, params):
            return False
        log.info("[cyan]param set[/cyan]: %s.%s=%s", name, key, params.get(key))
        return True

    # ---- event fan-out --------------------------------------------------
    def _collect(self, method: str, payload) -> list:
        signals = []
        for strat in list(self.strategies.values()):
            if not strat.enabled:
                continue
            try:
                signals.extend(getattr(strat, method)(payload))
            except Exception as exc:  # pragma: no cover - isolate strategy bugs
                log.error("strategy %s.%s error: %s", strat.name, method, exc)
        return signals

    async def run(self) -> None:
        from apex.core.models import MarketTick

        bus = await make_bus()
        log.info("Strategy-engine running: %s on %s", list(self.strategies), self.symbols)

        loop = asyncio.get_event_loop()

        async def pump(channel: str, method: str, decode, offload: bool = False):
            async for msg in bus.subscribe(channel):
                try:
                    payload = decode(msg)
                    # NEWS handlers may do blocking I/O (e.g. sniper honeypot
                    # screen); run them off the event loop so one slow call can't
                    # stall ticks/risk/heartbeat across the single-process deploy.
                    if offload:
                        signals = await loop.run_in_executor(None, self._collect, method, payload)
                    else:
                        signals = self._collect(method, payload)
                    for sig in signals:
                        await bus.publish(Channels.SIGNALS, sig.to_dict())
                except Exception as exc:  # one bad message must not kill the sub
                    log.warning("pump %s dropped a message: %s", channel, exc)

        async def commands():
            async for cmd in bus.subscribe(Channels.COMMANDS):
                try:
                    self._handle_command(cmd)
                except Exception as exc:
                    log.warning("command handler error: %s", exc)

        await asyncio.gather(
            pump(Channels.TICKS, "on_tick", MarketTick.from_dict),
            pump(Channels.NEWS, "on_news", lambda m: m, offload=True),
            pump(Channels.PREDICTIONS, "on_prediction", lambda m: m),
            commands(),
        )

    def _handle_command(self, cmd: dict) -> None:
        action = cmd.get("action")
        if action == "enable_strategy":
            self.enable(cmd["name"], **cmd.get("params", {}))
        elif action == "disable_strategy":
            self.disable(cmd["name"])
        elif action == "set_param":
            self.set_param(cmd["name"], cmd["key"], cmd["value"])
        elif action == "set_symbols":
            self.symbols = cmd["symbols"]
            self.store.set_symbols(cmd["symbols"])
            # rebuild all live strategies on the new symbol set
            for name in list(self.strategies):
                self._instantiate(name, self.store.params(name))
        elif action == "add_planner_rule":
            planner = self.strategies.get("planner")
            if planner is None or not hasattr(planner, "add_rule"):
                return
            # SECURITY: never trust a rule off the bus. Re-validate here so the
            # engine enforces sandbox + caps regardless of who published it
            # (defense in depth — the bus has no auth).
            from apex.ai.llm_planner import validate_rule
            safe = validate_rule(cmd.get("rule") or {})
            if not safe:
                log.warning("rejected unsafe planner rule from bus: %s", cmd.get("rule"))
                return
            try:
                planner.add_rule(safe)
                log.info("planner rule added (revalidated): %s", safe.get("name"))
            except Exception as exc:  # pragma: no cover
                log.warning("bad planner rule rejected: %s", exc)
        else:
            log.warning("strategy-engine: unknown COMMAND action %r (ignored)", action)


async def run(symbols: list[str] | None = None, enabled: list[str] | None = None) -> None:
    await StrategyEngine(symbols, enabled=enabled).run()
