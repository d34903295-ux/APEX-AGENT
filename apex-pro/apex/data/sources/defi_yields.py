"""DeFi yields source via the free DefiLlama API (https://yields.llama.fi/pools).

Produces NEWS items of type 'defi_yields' that the yield-farming strategy
consumes to rotate stablecoins into the best risk-adjusted, audited pools.
Pure parsing (`parse_llama_pools`) is testable without network.
"""
from __future__ import annotations

import json
import urllib.request
from collections import defaultdict

from apex.core.logging import get_logger

log = get_logger("apex.data.yields")

# Map DefiLlama project slugs to our audited allow-list keys.
PROJECT_MAP = {
    "aave-v3": "aave-v3", "aave": "aave-v3", "compound-v3": "compound-v3",
    "compound": "compound-v3", "lido": "lido", "curve-dex": "curve",
    "curve": "curve", "convex-finance": "convex", "yearn-finance": "yearn",
    "morpho-blue": "morpho", "morpho-aave": "morpho",
}
STABLES = {"USDC", "USDT", "DAI", "FRAX", "USDe"}


def parse_llama_pools(payload: dict, *, min_tvl: float = 5_000_000,
                      assets: set[str] | None = None) -> dict[str, list[dict]]:
    """Return {asset -> [pool, ...]} for audited projects above a TVL floor."""
    assets = assets or STABLES
    out: dict[str, list[dict]] = defaultdict(list)
    for p in (payload or {}).get("data", []):
        symbol = (p.get("symbol") or "").upper()
        proj = PROJECT_MAP.get(p.get("project", ""))
        if not proj or p.get("tvlUsd", 0) < min_tvl:
            continue
        asset = next((a for a in assets if a in symbol), None)
        if not asset:
            continue
        apy = p.get("apy")
        if apy is None:
            continue
        out[asset].append({
            "protocol": proj, "apy": float(apy) / 100.0,  # llama apy is in %
            "chain": (p.get("chain") or "").lower(), "tvl_usd": float(p.get("tvlUsd", 0)),
        })
    # Sort each asset's pools by apy desc.
    for a in out:
        out[a].sort(key=lambda d: d["apy"], reverse=True)
    return out


def fetch_yields(timeout: float = 8.0) -> dict[str, list[dict]]:
    try:
        with urllib.request.urlopen("https://yields.llama.fi/pools", timeout=timeout) as r:  # pragma: no cover
            payload = json.loads(r.read().decode())
        return parse_llama_pools(payload)
    except Exception as exc:
        log.warning("DefiLlama fetch failed: %s", exc)
        return {}
