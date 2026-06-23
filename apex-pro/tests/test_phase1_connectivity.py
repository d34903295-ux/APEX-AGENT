from __future__ import annotations

from apex.execution.adapters.base import classify_venue
from apex.execution.gateway import ExecutionGateway
from apex.strategies.honeypot import parse_goplus
from apex.data.sources.defi_yields import parse_llama_pools


# ---- venue classification & smart routing -----------------------------------
def test_classify_venue():
    assert classify_venue("binance") == "cex"
    assert classify_venue("uniswap") == "evm_dex"
    assert classify_venue("jupiter") == "solana_dex"
    assert classify_venue("totally-unknown") == "paper"


def test_best_venue_picks_cheapest_buy_and_richest_sell():
    gw = ExecutionGateway()
    gw.update_mark("BTC/USDT", 100.0, exchange="binance")
    gw.update_mark("BTC/USDT", 101.0, exchange="kraken")
    assert gw.best_venue("BTC/USDT", "buy") == "binance"
    assert gw.best_venue("BTC/USDT", "sell") == "kraken"
    assert gw.best_venue("ETH/USDT", "buy") is None


# ---- GoPlus honeypot parsing (fail-closed) ----------------------------------
def _goplus(token, **fields):
    base = {"is_honeypot": "0", "cannot_sell_all": "0", "buy_tax": "0.01",
            "sell_tax": "0.01", "can_take_back_ownership": "0",
            "owner_address": "0x0000000000000000000000000000000000000000",
            "dex": [{"liquidity": "50000"}],
            "lp_holders": [{"is_locked": "1", "percent": "0.9"}],
            "holders": [{"percent": "0.05"}]}
    base.update(fields)
    return {"result": {token.lower(): base}}


def test_goplus_safe_token():
    token = "0xABCdef0000000000000000000000000000000001"
    rep = parse_goplus(_goplus(token), token, "ethereum")
    assert rep.sellable is True
    assert rep.safe is True
    assert rep.score >= 0.6


def test_goplus_honeypot_is_unsafe():
    token = "0xBAD0000000000000000000000000000000000002"
    rep = parse_goplus(_goplus(token, is_honeypot="1"), token, "ethereum")
    assert rep.sellable is False
    assert rep.safe is False
    assert rep.score == 0.0


def test_goplus_missing_data_fails_closed():
    rep = parse_goplus({"result": {}}, "0xdead", "ethereum")
    assert rep.safe is False
    assert "no GoPlus data" in " ".join(rep.reasons)


def test_goplus_high_tax_flagged():
    token = "0xTAX0000000000000000000000000000000000003"
    rep = parse_goplus(_goplus(token, sell_tax="0.5"), token, "ethereum")
    assert any("tax" in r for r in rep.reasons)


# ---- DefiLlama yields parsing ----------------------------------------------
def test_parse_llama_pools_filters_and_sorts():
    payload = {"data": [
        {"symbol": "USDC", "project": "aave-v3", "chain": "Ethereum",
         "apy": 5.0, "tvlUsd": 100_000_000},
        {"symbol": "USDC", "project": "aave-v3", "chain": "Arbitrum",
         "apy": 8.0, "tvlUsd": 50_000_000},
        {"symbol": "USDC", "project": "sketchy-fork", "chain": "BSC",
         "apy": 200.0, "tvlUsd": 100_000},          # excluded: not allow-listed + low TVL
        {"symbol": "WETH", "project": "lido", "chain": "Ethereum",
         "apy": 3.0, "tvlUsd": 1_000_000_000},       # excluded: not a stable
    ]}
    out = parse_llama_pools(payload)
    assert "USDC" in out
    assert len(out["USDC"]) == 2
    assert out["USDC"][0]["apy"] == 0.08  # sorted desc, converted from %
    assert all(p["protocol"] == "aave-v3" for p in out["USDC"])
