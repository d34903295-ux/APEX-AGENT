"""Honeypot / rug-pull screener for fresh DEX tokens.

DEFENSIVE tool: keeps the sniper from buying tokens it can never sell. Wired to
the FREE GoPlus token-security API (no key required). Pure parsing is split out
(`parse_goplus`) so it is unit-testable without network, and the whole thing
FAILS CLOSED — any error or unknown == unsafe.
"""
from __future__ import annotations

import json
import urllib.request
from dataclasses import dataclass, field

from apex.core.logging import get_logger

log = get_logger("apex.honeypot")

# GoPlus chain ids.
CHAIN_IDS = {
    "ethereum": "1", "eth": "1", "bsc": "56", "polygon": "137",
    "arbitrum": "42161", "base": "8453", "optimism": "10", "avalanche": "43114",
}


@dataclass
class HoneypotReport:
    token: str
    chain: str
    sellable: bool = False
    buy_tax: float = 1.0
    sell_tax: float = 1.0
    liquidity_usd: float = 0.0
    lp_locked: bool = False
    ownership_renounced: bool = False
    top_holder_pct: float = 1.0
    reasons: list[str] = field(default_factory=list)

    @property
    def score(self) -> float:
        s = 1.0
        if not self.sellable:
            return 0.0
        s -= min(0.5, (self.buy_tax + self.sell_tax))
        if not self.lp_locked:
            s -= 0.2
        if not self.ownership_renounced:
            s -= 0.1
        if self.top_holder_pct > 0.5:
            s -= 0.3
        return max(0.0, min(1.0, s))

    @property
    def safe(self) -> bool:
        return self.score >= 0.6 and self.sellable

    def as_dict(self) -> dict:
        return {
            "sellable": self.sellable, "buy_tax": self.buy_tax,
            "sell_tax": self.sell_tax, "liquidity_usd": self.liquidity_usd,
            "lp_locked": self.lp_locked, "ownership_renounced": self.ownership_renounced,
            "top_holder_pct": self.top_holder_pct, "score": self.score,
            "reasons": self.reasons,
        }


def _f(v, default=0.0) -> float:
    try:
        return float(v)
    except (TypeError, ValueError):
        return default


def parse_goplus(payload: dict, token: str, chain: str,
                 *, min_liquidity_usd: float = 25_000, max_tax: float = 0.10) -> HoneypotReport:
    """Pure parser for a GoPlus token_security response. Fail-closed on missing data."""
    report = HoneypotReport(token=token, chain=chain)
    result = (payload or {}).get("result", {})
    # GoPlus keys the result by the lowercased contract address.
    data = result.get(token.lower()) or (next(iter(result.values()), None) if result else None)
    if not data:
        report.reasons.append("no GoPlus data for token")
        return report

    is_honeypot = str(data.get("is_honeypot", "1")) == "1"
    cannot_sell_all = str(data.get("cannot_sell_all", "0")) == "1"
    report.sellable = (not is_honeypot) and (not cannot_sell_all)
    report.buy_tax = _f(data.get("buy_tax"), 1.0)
    report.sell_tax = _f(data.get("sell_tax"), 1.0)
    report.ownership_renounced = (
        str(data.get("can_take_back_ownership", "1")) == "0"
        and data.get("owner_address", "") in ("", "0x0000000000000000000000000000000000000000")
    )

    # Liquidity + LP lock from the DEX/lp holder lists when present.
    dex = data.get("dex") or []
    report.liquidity_usd = sum(_f(d.get("liquidity")) for d in dex) if dex else 0.0
    lp_holders = data.get("lp_holders") or []
    report.lp_locked = any(
        str(h.get("is_locked", "0")) == "1" or _f(h.get("percent")) > 0.5
        for h in lp_holders
    )
    holders = data.get("holders") or []
    report.top_holder_pct = max((_f(h.get("percent")) for h in holders), default=1.0)

    if not report.sellable:
        report.reasons.append("honeypot / cannot sell all")
    if report.buy_tax > max_tax or report.sell_tax > max_tax:
        report.reasons.append(f"tax too high (buy={report.buy_tax}, sell={report.sell_tax})")
    if report.liquidity_usd < min_liquidity_usd:
        report.reasons.append(f"low liquidity ${report.liquidity_usd:.0f}")
    return report


def screen_token(token: str, chain: str = "ethereum", *,
                 min_liquidity_usd: float = 25_000, max_tax: float = 0.10,
                 timeout: float = 6.0) -> HoneypotReport:
    """Screen via GoPlus. Network errors -> UNSAFE report (fail closed)."""
    chain_id = CHAIN_IDS.get(chain.lower())
    if not chain_id:
        r = HoneypotReport(token=token, chain=chain)
        r.reasons.append(f"unsupported chain {chain}")
        return r
    url = (f"https://api.gopluslabs.io/api/v1/token_security/{chain_id}"
           f"?contract_addresses={token}")
    try:
        with urllib.request.urlopen(url, timeout=timeout) as resp:  # pragma: no cover - network
            payload = json.loads(resp.read().decode())
        return parse_goplus(payload, token, chain,
                            min_liquidity_usd=min_liquidity_usd, max_tax=max_tax)
    except Exception as exc:
        log.warning("GoPlus screen failed for %s (%s); marking UNSAFE", token, exc)
        r = HoneypotReport(token=token, chain=chain)
        r.reasons.append(f"screen error: {exc}")
        return r
