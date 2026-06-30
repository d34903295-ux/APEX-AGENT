"""User-editable strategy configuration — file-backed and hot-reloadable.

Lets the *user* (not a developer) decide which strategies run, with which
parameters and on which symbols — via a JSON file they can edit, or live over
Telegram. Changes persist across restarts.

Schema (data/strategy_config.json):
    {
      "symbols": ["BTC/USDT", "ETH/USDT"],
      "strategies": {
        "grid": {"enabled": true,  "params": {"levels": 6, "base_spacing": 0.005}},
        "dca":  {"enabled": true,  "params": {}},
        "scalping": {"enabled": false, "params": {}}
      }
    }
"""
from __future__ import annotations

import json
from pathlib import Path

from apex.core.logging import get_logger

log = get_logger("apex.strategies.store")

DEFAULT_SYMBOLS = ["BTC/USDT", "ETH/USDT", "SOL/USDT"]

# Sensible per-profile starting rosters the user can then tweak.
PROFILE_ROSTERS = {
    "conservative": ["grid", "dca"],
    "balanced": ["grid", "dca", "portfolio"],
    "aggressive": ["grid", "dca", "scalping", "onchain", "news"],
    "degen": ["scalping", "sniper", "news", "onchain", "arbitrage", "planner"],
}


def coerce(value):
    """Coerce a string (e.g. from Telegram) into bool/int/float/str."""
    if not isinstance(value, str):
        return value
    v = value.strip()
    if v.lower() in {"true", "false"}:
        return v.lower() == "true"
    for cast in (int, float):
        try:
            return cast(v)
        except ValueError:
            continue
    return v


class StrategyConfigStore:
    def __init__(self, path: str = "./data/strategy_config.json"):
        self.path = Path(path)
        self.data: dict = {"symbols": list(DEFAULT_SYMBOLS), "strategies": {}}

    # ---- persistence ----------------------------------------------------
    def load(self, default_roster: list[str] | None = None) -> "StrategyConfigStore":
        if self.path.exists():
            try:
                self.data = json.loads(self.path.read_text())
                log.info("loaded strategy config from %s", self.path)
                return self
            except Exception as exc:  # pragma: no cover
                log.warning("bad strategy config (%s); seeding defaults", exc)
        # Seed defaults.
        for name in (default_roster or PROFILE_ROSTERS["conservative"]):
            self.data["strategies"][name] = {"enabled": True, "params": {}}
        self.save()
        return self

    def save(self) -> None:
        try:
            self.path.parent.mkdir(parents=True, exist_ok=True)
            self.path.write_text(json.dumps(self.data, indent=2))
        except Exception as exc:  # pragma: no cover
            log.warning("could not persist strategy config: %s", exc)

    # ---- accessors ------------------------------------------------------
    @property
    def symbols(self) -> list[str]:
        return self.data.get("symbols", list(DEFAULT_SYMBOLS))

    def set_symbols(self, symbols: list[str]) -> None:
        self.data["symbols"] = symbols
        self.save()

    def enabled(self) -> dict[str, dict]:
        return {name: cfg.get("params", {})
                for name, cfg in self.data["strategies"].items()
                if cfg.get("enabled")}

    def all(self) -> dict[str, dict]:
        return self.data["strategies"]

    # ---- mutations ------------------------------------------------------
    def enable(self, name: str, params: dict | None = None) -> None:
        cfg = self.data["strategies"].setdefault(name, {"enabled": False, "params": {}})
        cfg["enabled"] = True
        if params:
            cfg["params"].update(params)
        self.save()

    def disable(self, name: str) -> None:
        if name in self.data["strategies"]:
            self.data["strategies"][name]["enabled"] = False
            self.save()

    def set_param(self, name: str, key: str, value) -> dict:
        cfg = self.data["strategies"].setdefault(name, {"enabled": False, "params": {}})
        cfg["params"][key] = coerce(value)
        self.save()
        return cfg["params"]

    def params(self, name: str) -> dict:
        return self.data["strategies"].get(name, {}).get("params", {})
