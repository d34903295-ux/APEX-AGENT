"""Microservice entrypoint: ai-brain."""
from __future__ import annotations

import asyncio

from apex.ai.brain import run
from apex.data.feeder import DEFAULT_SYMBOLS

if __name__ == "__main__":
    asyncio.run(run(DEFAULT_SYMBOLS))
