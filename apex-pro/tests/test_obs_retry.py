from __future__ import annotations

import pytest

from apex.obs.retry import retry_async, retry_sync


def test_retry_sync_succeeds_after_failures():
    calls = {"n": 0}

    def flaky():
        calls["n"] += 1
        if calls["n"] < 3:
            raise ValueError("boom")
        return "ok"

    out = retry_sync(flaky, attempts=5, base=2.0, _sleep=lambda d: None)
    assert out == "ok"
    assert calls["n"] == 3


def test_retry_sync_raises_after_exhaustion():
    def always_fail():
        raise RuntimeError("nope")

    with pytest.raises(RuntimeError):
        retry_sync(always_fail, attempts=3, _sleep=lambda d: None)


@pytest.mark.asyncio
async def test_retry_async_succeeds_on_second_try():
    calls = {"n": 0}

    async def flaky():
        calls["n"] += 1
        if calls["n"] < 2:
            raise ValueError("boom")
        return 42

    # attempts=3; first retry delay is 0.0 so no real sleep occurs.
    out = await retry_async(flaky, attempts=3)
    assert out == 42
    assert calls["n"] == 2


@pytest.mark.asyncio
async def test_retry_async_raises_after_exhaustion():
    async def always_fail():
        raise KeyError("x")

    with pytest.raises(KeyError):
        await retry_async(always_fail, attempts=2)  # only the 0-delay retry
