"""Derivatives / flow source from PUBLIC exchange endpoints (no API key).

Aggregates, per symbol:
  * funding_rate   — Binance Futures premiumIndex.lastFundingRate
  * open_interest  — Binance Futures openInterest
  * cvd_slope      — cumulative volume delta from public aggTrades
                     (buyer-maker == sell-aggressor)

Publishes NEWS items of type 'onchain' consumed by the onchain_flow strategy.
Pure parsers are split out for unit testing without network. Everything degrades
gracefully (network error -> neutral/empty).

NOTE: exchange_netflow_z (true on-chain stablecoin flows) needs a data provider
and stays 0 here; funding/OI/CVD already give a usable derivatives-flow bias.
"""
from __future__ import annotations

import json
import urllib.request

from apex.core.logging import get_logger

log = get_logger("apex.data.deriv")

FAPI = "https://fapi.binance.com"


def to_binance_perp(symbol: str) -> str:
    """'BTC/USDT' -> 'BTCUSDT'."""
    return symbol.replace("/", "").upper()


def parse_funding(payload: dict) -> float:
    try:
        return float(payload.get("lastFundingRate", 0.0))
    except (TypeError, ValueError):
        return 0.0


def parse_open_interest(payload: dict) -> float:
    try:
        return float(payload.get("openInterest", 0.0))
    except (TypeError, ValueError):
        return 0.0


def parse_cvd_slope(agg_trades: list[dict]) -> float:
    """Normalised CVD over the window: (buy_vol - sell_vol) / total_vol in [-1,1].

    Binance aggTrade flag 'm' = True means the buyer is the market maker, i.e.
    the trade was SELL-aggressor. So m==False -> buy pressure.
    """
    buy = sell = 0.0
    for t in agg_trades:
        try:
            qty = float(t.get("q", 0))
        except (TypeError, ValueError):
            continue
        if t.get("m"):
            sell += qty
        else:
            buy += qty
    total = buy + sell
    if total == 0:
        return 0.0
    return (buy - sell) / total


def _get(url: str, timeout: float) -> object:
    with urllib.request.urlopen(url, timeout=timeout) as r:  # pragma: no cover - network
        return json.loads(r.read().decode())


def fetch_symbol_flow(symbol: str, *, timeout: float = 6.0) -> dict:
    """Return an 'onchain' NEWS payload for one symbol (best-effort)."""
    perp = to_binance_perp(symbol)
    funding = cvd = 0.0
    oi = 0.0
    try:  # pragma: no cover - network
        funding = parse_funding(_get(f"{FAPI}/fapi/v1/premiumIndex?symbol={perp}", timeout))
        oi = parse_open_interest(_get(f"{FAPI}/fapi/v1/openInterest?symbol={perp}", timeout))
        cvd = parse_cvd_slope(_get(f"{FAPI}/fapi/v1/aggTrades?symbol={perp}&limit=1000", timeout))
    except Exception as exc:
        log.warning("derivatives flow fetch failed for %s: %s", symbol, exc)
    return {
        "type": "onchain", "symbol": symbol,
        "funding_rate": funding, "open_interest": oi,
        "cvd_slope": cvd, "exchange_netflow_z": 0.0,
    }
