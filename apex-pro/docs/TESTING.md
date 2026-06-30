# Testing & Validation Strategy — "don't self-destruct"

A trading agent that loses money correctly is worse than one that crashes. This
is the gauntlet every strategy and release must pass.

## Layers

### 1. Unit tests (`pytest -q`)
Fast, deterministic, no network. They specifically assert the **safety
invariants**:

- `test_risk.py` — position sizing is capped by profile; over-leverage is
  rejected; pause blocks all orders; abnormal regime auto-pauses; degen leverage
  is unlocked **but bounded** by an absolute ceiling.
- `test_montecarlo_and_kelly.py` — Kelly stays in `[0,1]`; Monte Carlo flags
  ruin for negative-edge systems and clears small positive-edge ones.
- `test_paper_and_portfolio.py` — fills, cash accounting and realised PnL.
- `test_backtest.py` — end-to-end replay produces sane stats + Monte Carlo.
- `test_strategies.py` — all strategies register; planner rules fire; **ethics
  guard**: the MEV module exposes no sandwich/victim-frontrunning hook.
- `test_bus.py` — pub/sub delivery.

```bash
pip install pytest pytest-asyncio
pytest -q
```

### 2. Backtest (historical)
`apex/backtest/engine.py::run_backtest(strategy, prices)` replays a price series
through the **real** strategy → risk-manager → paper-executor path and returns
return %, max drawdown, win rate and a Monte Carlo on the trade distribution.

### 3. Monte Carlo gate
`risk/montecarlo.simulate(...)` returns `safe_to_go_live` — requires
`prob_ruin < 1%` and `median_max_drawdown < 35%`. A strategy that fails the
gate is **never** allocated real capital.

### 4. Forward test (paper, mandatory 24h)
Before any new strategy trades real money it must run **24h in paper mode** on
live data. Enable it with `/set_strategy on <name>` while `APEX_MODE=paper`,
watch `/performance`, and only then consider live.

## The promotion checklist (manual gate before live)

```
[ ] Unit tests green                      (pytest -q)
[ ] Backtest: positive expectancy, DD acceptable
[ ] Monte Carlo: safe_to_go_live == True
[ ] 24h paper forward-test: positive, no auto-pauses from the strategy
[ ] Risk caps reviewed for the chosen profile
[ ] Telegram /pause verified to stop the agent
[ ] Trade-only API keys (withdrawals disabled), dedicated hot wallet
[ ] Start with a tiny live allocation; scale only after a week of live paper-parity
```

## Continuous integration
`.github/workflows/apex-pro-ci.yml` runs the suite on every push/PR touching
`apex-pro/`.

## Chaos / failure drills (recommended before live)
- Kill `redis` mid-run → confirm services reconnect / in-proc fallback.
- Feed a price spike → confirm regime auto-pause fires and Telegram alerts.
- Revoke an API key → confirm gateway fails closed (no silent retries as paper
  for *live* orders; it logs and drops).
