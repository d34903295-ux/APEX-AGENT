"""Microservice entrypoint: telegram-commander.

Runs standalone (no in-process RiskManager) — it reads state from the Redis
heartbeat and issues commands over the bus.
"""
from __future__ import annotations

import asyncio

from apex.telegram.bot import run_bot

if __name__ == "__main__":
    asyncio.run(run_bot())
