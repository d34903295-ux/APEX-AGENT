# Configuring Your Strategy (no code required)

APEX is built so **the operator — not a developer — decides how it trades**.
There are three ways to configure it, all without touching Python.

## 1. Risk profile (the big switch) — `.env`

```ini
APEX_RISK_PROFILE=conservative   # conservative | balanced | aggressive | degen
```

The profile seeds a starting strategy roster and sets the hard risk caps
(position size, leverage, drawdown). On first run the agent writes a config
file you can then fine-tune. Default rosters:

| Profile | Strategies enabled by default |
|---|---|
| conservative | grid, dca |
| balanced | grid, dca, portfolio |
| aggressive | grid, dca, scalping, onchain, news |
| degen | scalping, sniper, news, onchain, arbitrage, planner |

## 2. Strategy config file — `data/strategy_config.json`

Auto-created on first boot (seeded from your profile). Edit it and restart, or
point somewhere else with `APEX_STRATEGY_CONFIG=/path/to/file.json`. A fully
worked example with every tunable is in
[`config/strategies.example.json`](../config/strategies.example.json).

```jsonc
{
  "symbols": ["BTC/USDT", "ETH/USDT"],
  "strategies": {
    "grid": { "enabled": true,  "params": { "levels": 8, "base_spacing": 0.004 } },
    "dca":  { "enabled": true,  "params": { "slow": 120 } },
    "scalping": { "enabled": false, "params": {} }
  }
}
```

Every key under `params` is passed straight to that strategy's constructor — see
each strategy in `apex/strategies/` for its tunables.

## 3. Live, from Telegram (no restart)

| Command | Effect |
|---|---|
| `/strategies` | List all strategies, which are on, and their params |
| `/set_strategy on\|off <name>` | Enable/disable a strategy instantly |
| `/set_param <name> <key> <value>` | Tune a parameter live (e.g. `/set_param grid levels 8`) |
| `/params <name>` | Show current params for a strategy |
| `/symbols` | Show traded symbols |
| `/symbols BTC/USDT ETH/USDT` | Change the traded symbol set |
| `/risk_profile <profile>` | Switch risk profile (degen needs 2FA + CONFIRM) |

All live changes are **persisted** back to the config file, so they survive a
restart. Values are auto-typed (`8`→int, `0.004`→float, `true`→bool).

## How it flows
`Telegram → COMMANDS bus → strategy-engine applies live + saves to JSON`.
On boot the engine loads the same JSON, so the file and the live state are
always one and the same source of truth.
