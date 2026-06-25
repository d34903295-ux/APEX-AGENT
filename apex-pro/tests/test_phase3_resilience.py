from __future__ import annotations

import pytest

from apex.execution.circuit import CircuitBreaker, State, VenueFailover
from apex.obs.http import get_json


class FakeClock:
    def __init__(self):
        self.t = 0.0

    def __call__(self):
        return self.t

    def advance(self, dt):
        self.t += dt


def test_circuit_opens_after_threshold_and_recovers():
    clk = FakeClock()
    cb = CircuitBreaker(threshold=3, cooldown=30, clock=clk)
    assert cb.allow()
    cb.record_failure(); cb.record_failure()
    assert cb.state is State.CLOSED and cb.allow()      # under threshold
    cb.record_failure()
    assert cb.state is State.OPEN and not cb.allow()    # tripped

    clk.advance(31)
    assert cb.allow()                                   # half-open probe allowed
    assert cb.state is State.HALF_OPEN
    cb.record_success()
    assert cb.state is State.CLOSED


def test_circuit_halfopen_failure_reopens():
    clk = FakeClock()
    cb = CircuitBreaker(threshold=1, cooldown=10, clock=clk)
    cb.record_failure()
    assert cb.state is State.OPEN
    clk.advance(11)
    assert cb.allow() and cb.state is State.HALF_OPEN
    cb.record_failure()
    assert cb.state is State.OPEN


def test_failover_skips_open_venues():
    clk = FakeClock()
    fo = VenueFailover(threshold=1, cooldown=100, clock=clk)
    # binance trips after one failure -> dropped from candidates.
    fo.record_failure("binance")
    cands = fo.candidates("binance", ["bybit", "okx"])
    assert "binance" not in cands
    assert cands == ["bybit", "okx"]


def test_failover_candidates_dedup_and_order():
    fo = VenueFailover()
    assert fo.candidates("binance", ["binance", "kraken", "kraken"]) == ["binance", "kraken"]


# ---- resilient HTTP --------------------------------------------------------
def test_get_json_retries_then_succeeds():
    calls = {"n": 0}

    class _Resp:
        def __enter__(self): return self
        def __exit__(self, *a): return False
        def read(self): return b'{"ok": true}'

    def opener(url, timeout):
        calls["n"] += 1
        if calls["n"] < 2:
            raise OSError("connection reset")
        return _Resp()

    out = get_json("http://x", attempts=3, _opener=opener, _sleep=lambda d: None)
    assert out == {"ok": True}
    assert calls["n"] == 2


def test_get_json_raises_after_exhaustion():
    def opener(url, timeout):
        raise OSError("down")

    with pytest.raises(OSError):
        get_json("http://x", attempts=2, _opener=opener, _sleep=lambda d: None)
