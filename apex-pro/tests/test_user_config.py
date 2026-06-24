from __future__ import annotations

from apex.strategies.engine import StrategyEngine
from apex.strategies.store import StrategyConfigStore, coerce


def test_coerce_types():
    assert coerce("true") is True
    assert coerce("false") is False
    assert coerce("8") == 8
    assert coerce("0.005") == 0.005
    assert coerce("BTC/USDT") == "BTC/USDT"


def test_store_seeds_defaults_and_persists(tmp_path):
    path = tmp_path / "cfg.json"
    store = StrategyConfigStore(str(path)).load(default_roster=["grid", "dca"])
    assert path.exists()
    assert set(store.enabled()) == {"grid", "dca"}

    # Reload from disk -> same state.
    store2 = StrategyConfigStore(str(path)).load()
    assert set(store2.enabled()) == {"grid", "dca"}


def test_store_enable_disable_setparam(tmp_path):
    store = StrategyConfigStore(str(tmp_path / "c.json")).load(default_roster=["grid"])
    store.disable("grid")
    assert "grid" not in store.enabled()
    store.enable("scalping", {"size_pct": 0.02})
    assert store.enabled()["scalping"]["size_pct"] == 0.02
    params = store.set_param("scalping", "obi_threshold", "0.3")
    assert params["obi_threshold"] == 0.3   # coerced to float


def test_engine_hot_setparam_rebuilds_strategy(tmp_path):
    store = StrategyConfigStore(str(tmp_path / "c.json")).load(default_roster=["grid"])
    engine = StrategyEngine(symbols=["BTC/USDT"], store=store)
    assert engine.strategies["grid"].levels == 6           # default
    engine._handle_command({"action": "set_param", "name": "grid",
                            "key": "levels", "value": "9"})
    assert engine.strategies["grid"].levels == 9           # hot-rebuilt
    # persisted
    assert StrategyConfigStore(str(tmp_path / "c.json")).load().params("grid")["levels"] == 9


def test_engine_enable_disable_via_command(tmp_path):
    store = StrategyConfigStore(str(tmp_path / "c.json")).load(default_roster=["grid"])
    engine = StrategyEngine(symbols=["BTC/USDT"], store=store)
    engine._handle_command({"action": "enable_strategy", "name": "dca", "params": {}})
    assert "dca" in engine.strategies
    engine._handle_command({"action": "disable_strategy", "name": "grid"})
    assert "grid" not in engine.strategies
    assert "grid" not in store.enabled()
