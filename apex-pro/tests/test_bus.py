from __future__ import annotations

import asyncio

import pytest

from apex.bus.redis_bus import InProcessBus


@pytest.mark.asyncio
async def test_inprocess_bus_pubsub():
    bus = InProcessBus()
    received = []

    async def listener():
        async for msg in bus.subscribe("ch"):
            received.append(msg)
            break

    task = asyncio.create_task(listener())
    await asyncio.sleep(0.01)
    await bus.publish("ch", {"hello": "world"})
    await asyncio.wait_for(task, timeout=1)
    assert received == [{"hello": "world"}]
