"""New-token / new-pool detector via the FREE DexScreener API (no key).

Polls DexScreener's latest token profiles and emits 'new_pool' NEWS items. The
sniper strategy receives them and runs the GoPlus honeypot screen before any
buy signal — so this feed is just *discovery*, never a buy trigger by itself.

Pure parser (`parse_dexscreener_profiles`) is unit-testable without network.
"""
from __future__ import annotations

import json
import urllib.request

from apex.core.logging import get_logger

log = get_logger("apex.data.newpools")

PROFILES_URL = "https://api.dexscreener.com/token-profiles/latest/v1"

# DexScreener chainId -> our chain names (used by the honeypot screener).
CHAIN_MAP = {
    "ethereum": "ethereum", "bsc": "bsc", "polygon": "polygon",
    "arbitrum": "arbitrum", "base": "base", "optimism": "optimism",
    "avalanche": "avalanche", "solana": "solana",
}


def parse_dexscreener_profiles(payload, *, chains: set[str] | None = None) -> list[dict]:
    """Turn the profiles list into 'new_pool' NEWS items."""
    items: list[dict] = []
    if not isinstance(payload, list):
        return items
    for entry in payload:
        token = entry.get("tokenAddress")
        chain = CHAIN_MAP.get((entry.get("chainId") or "").lower())
        if not token or not chain:
            continue
        if chains and chain not in chains:
            continue
        items.append({
            "type": "new_pool",
            "token_address": token,
            "chain": chain,
            "symbol": token[:8],
            "dex": "uniswap" if chain != "solana" else "jupiter",
            "url": entry.get("url", ""),
        })
    return items


def fetch_new_pools(*, chains: set[str] | None = None, timeout: float = 6.0) -> list[dict]:
    try:  # pragma: no cover - network
        with urllib.request.urlopen(PROFILES_URL, timeout=timeout) as r:
            payload = json.loads(r.read().decode())
        return parse_dexscreener_profiles(payload, chains=chains)
    except Exception as exc:
        log.warning("DexScreener fetch failed: %s", exc)
        return []
