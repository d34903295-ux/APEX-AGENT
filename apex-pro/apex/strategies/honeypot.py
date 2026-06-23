"""Honeypot / rug-pull screener for fresh DEX tokens.

This is a *defensive* tool: it tries to keep the sniper from buying tokens it
can never sell. The probes below are stubs that return a structured report;
wire them to real RPC calls (eth_call sell-simulation, GoPlus/Honeypot.is
APIs, LP-lock checks) in `execution/onchain_*`.
"""
from __future__ import annotations

from dataclasses import dataclass, field


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
        """0..1 confidence that the token is safe to trade."""
        s = 1.0
        if not self.sellable:
            s = 0.0
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


def screen_token(token: str, chain: str = "ethereum", *,
                 min_liquidity_usd: float = 25_000, max_tax: float = 0.10) -> HoneypotReport:
    """Run the screen. STUB: returns an unsafe report until RPC probes are wired.

    Replace the body with real probes:
      1. simulate a buy then a sell via eth_call against a fork/RPC
      2. read taxes from the simulation deltas
      3. check LP lock (Unicrypt/Team.Finance), ownership (owner() == 0x0)
      4. query holder distribution (covalent/explorer)
    """
    report = HoneypotReport(token=token, chain=chain)
    report.reasons.append("screen not yet wired to RPC — defaulting to UNSAFE")
    # Fail-closed: unknown == unsafe. Never buy what we couldn't verify.
    return report
