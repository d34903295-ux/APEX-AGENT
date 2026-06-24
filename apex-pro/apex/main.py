"""All-in-one orchestrator (single process).

Runs every microservice in one asyncio event loop over the in-process bus.
This is the "clone and run in 30 minutes" entrypoint:

    python -m apex.main

For a distributed deployment, run each service container separately (see
docker-compose.yml) — they communicate over Redis instead.
"""
from __future__ import annotations

import asyncio
import os

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.config import get_settings
from apex.core.logging import get_logger
from apex.data.feeder import DEFAULT_SYMBOLS
from apex.data import feeder
from apex.execution.gateway import ExecutionGateway
from apex.risk.manager import RiskManager
from apex.services import execution_gateway, risk_manager
from apex.strategies.engine import StrategyEngine
from apex.strategies.store import PROFILE_ROSTERS, StrategyConfigStore

log = get_logger("apex.main")
BANNER = r"""
   _   ___ _____  __    ___ ___  ___
  /_\ | _ \ __\ \/ /   | _ \ _ \/ _ \   autonomous multi-asset agent
 / _ \|  _/ _| >  <    |  _/   / (_) |  mode=%s profile=%s live=%s
/_/ \_\_| |___/_/\_\   |_| |_|_\\___/   strategies=%s
"""


async def _heartbeat(rm: RiskManager) -> None:
    """Publish portfolio snapshots so Telegram/dashboard can read state."""
    bus = await make_bus()
    while True:
        await bus.publish(Channels.HEARTBEAT, {
            "type": "portfolio", "paused": rm.paused, "reason": rm.pause_reason,
            "snapshot": rm.pf.snapshot(),
        })
        await asyncio.sleep(5)


async def main() -> None:
    s = get_settings()
    symbols = DEFAULT_SYMBOLS

    # Shared stateful components (single source of truth in-process).
    rm = RiskManager(settings=s)
    gw = ExecutionGateway(settings=s)
    store = StrategyConfigStore(
        os.getenv("APEX_STRATEGY_CONFIG", "./data/strategy_config.json")
    ).load(default_roster=PROFILE_ROSTERS.get(s.risk_profile.value))
    engine = StrategyEngine(symbols, store=store)

    log.info(BANNER, s.mode.value, s.risk_profile.value, s.is_live, list(engine.strategies))
    if s.is_live:
        log.warning("[bold red]LIVE TRADING ENABLED — real funds at risk[/bold red]")
    else:
        log.info("[green]Running in PAPER mode — no real funds at risk[/green]")

    from apex.ai import brain

    tasks = [
        feeder.run(symbols),
        engine.run(),
        risk_manager.run(rm),
        execution_gateway.run(gw),
        brain.run(symbols),
        _heartbeat(rm),
    ]

    # Telegram is optional — only start if a token is configured.
    if s.telegram_token:
        from apex.telegram.bot import run_bot
        tasks.append(run_bot(rm=rm))
    else:
        log.info("Telegram disabled (no TELEGRAM_BOT_TOKEN)")

    await asyncio.gather(*tasks)


if __name__ == "__main__":
    try:
        asyncio.run(main())
    except KeyboardInterrupt:
        log.info("shutdown requested")
