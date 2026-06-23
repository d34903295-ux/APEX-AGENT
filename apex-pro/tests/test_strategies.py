from __future__ import annotations

from apex.core.models import MarketTick
from apex.strategies import available_strategies
from apex.core.registry import STRATEGY_REGISTRY


def test_all_strategies_register():
    names = available_strategies()
    for expected in ["grid", "dca", "scalping", "arbitrage", "sniper", "mev",
                     "news", "onchain", "yield", "portfolio", "planner"]:
        assert expected in names


def test_grid_emits_signals_on_movement():
    grid = STRATEGY_REGISTRY.create("grid", symbols=["BTC/USDT"])
    signals = []
    price = 100.0
    for i in range(200):
        price *= 1.002 if i % 2 == 0 else 0.999
        signals += grid.on_tick(MarketTick(symbol="BTC/USDT", price=price))
    assert len(signals) > 0


def test_planner_rule_fires():
    spec = {
        "name": "btc_dip_buy_eth",
        "conditions": [{"fact": "BTC/USDT.change_1h", "op": "<", "value": -0.05}],
        "symbol": "ETH/USDT", "side": "buy", "leverage": 2.0, "sandboxed": True,
    }
    planner = STRATEGY_REGISTRY.create("planner", symbols=["ETH/USDT"], rules=[spec])
    planner.update_context({"BTC/USDT": {"change_1h": -0.06}})
    out = planner.on_prediction({"facts": {}})
    assert out and out[0].symbol == "ETH/USDT"
    assert out[0].meta["sandboxed"] is True


def test_mev_has_no_sandwich_hook():
    # Ethics guard: the MEV module must not expose victim-frontrunning.
    import apex.strategies.mev as mev
    src = open(mev.__file__).read().lower()
    assert "sandwich" in src  # only mentioned in the prohibition note
    assert "def sandwich" not in src
    assert "frontrun_victim" not in src
