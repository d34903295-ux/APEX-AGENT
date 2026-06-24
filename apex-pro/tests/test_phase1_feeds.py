from __future__ import annotations

from apex.data.sources.derivatives import (
    parse_cvd_slope, parse_funding, parse_open_interest, to_binance_perp,
)
from apex.data.sources.new_pools import parse_dexscreener_profiles


def test_binance_perp_symbol():
    assert to_binance_perp("BTC/USDT") == "BTCUSDT"
    assert to_binance_perp("eth/usdt") == "ETHUSDT"


def test_parse_funding_and_oi():
    assert parse_funding({"lastFundingRate": "0.0001"}) == 0.0001
    assert parse_funding({}) == 0.0
    assert parse_open_interest({"openInterest": "12345.6"}) == 12345.6
    assert parse_open_interest({"bad": 1}) == 0.0


def test_cvd_slope_buy_pressure():
    # m == False => buy aggressor
    trades = [{"q": "10", "m": False}, {"q": "5", "m": True}]
    slope = parse_cvd_slope(trades)
    assert abs(slope - (10 - 5) / 15) < 1e-9


def test_cvd_slope_empty_is_neutral():
    assert parse_cvd_slope([]) == 0.0
    assert parse_cvd_slope([{"q": "0", "m": True}]) == 0.0


def test_dexscreener_parse_filters_chains():
    payload = [
        {"chainId": "ethereum", "tokenAddress": "0xAAA", "url": "u1"},
        {"chainId": "solana", "tokenAddress": "SoLmint", "url": "u2"},
        {"chainId": "unknownchain", "tokenAddress": "0xBBB"},
        {"chainId": "bsc"},  # missing token -> skipped
    ]
    items = parse_dexscreener_profiles(payload)
    addrs = {i["token_address"] for i in items}
    assert addrs == {"0xAAA", "SoLmint"}
    eth = next(i for i in items if i["token_address"] == "0xAAA")
    assert eth["type"] == "new_pool" and eth["dex"] == "uniswap"
    sol = next(i for i in items if i["token_address"] == "SoLmint")
    assert sol["dex"] == "jupiter"


def test_dexscreener_chain_filter():
    payload = [{"chainId": "ethereum", "tokenAddress": "0xAAA"},
               {"chainId": "solana", "tokenAddress": "SoL"}]
    items = parse_dexscreener_profiles(payload, chains={"ethereum"})
    assert len(items) == 1 and items[0]["chain"] == "ethereum"


def test_dexscreener_handles_bad_payload():
    assert parse_dexscreener_profiles(None) == []
    assert parse_dexscreener_profiles({"not": "a list"}) == []
