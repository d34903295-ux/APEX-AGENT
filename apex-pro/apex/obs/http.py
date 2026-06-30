"""Resilient HTTP JSON GET with retry/backoff (auto-recovery for data feeds).

Centralises the urllib + retry pattern used by every public data source
(GoPlus, DefiLlama, DexScreener, Binance public). Injectable opener makes it
unit-testable without network.
"""
from __future__ import annotations

import json
import urllib.request

from apex.obs.retry import retry_sync


def get_json(url: str, *, timeout: float = 6.0, attempts: int = 3,
             base: float = 1.0, _opener=urllib.request.urlopen, _sleep=None):
    """GET url and parse JSON, retrying transient failures. Raises on final fail."""
    def _do():
        with _opener(url, timeout=timeout) as resp:
            return json.loads(resp.read().decode())

    kwargs = {"attempts": attempts, "base": base, "label": f"GET {url[:60]}"}
    if _sleep is not None:
        kwargs["_sleep"] = _sleep
    return retry_sync(_do, **kwargs)
