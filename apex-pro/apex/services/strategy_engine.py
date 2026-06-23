"""Microservice entrypoint: strategy-engine."""
from __future__ import annotations

import asyncio

from apex.data.feeder import DEFAULT_SYMBOLS
from apex.strategies.engine import run

if __name__ == "__main__":
    asyncio.run(run(DEFAULT_SYMBOLS))
