# APEX-AGENT PRO — Living Roadmap

> Updated continuously. Status: ✅ done · 🟡 functional/partial · ⬜ planned.
> Last update: 2026-06-23.

## Phase 0 — Foundation ✅ (this release)
- ✅ Event-driven microservice architecture (Redis Pub/Sub + in-proc fallback)
- ✅ Domain models, plugin registry, hot-swap strategy engine
- ✅ Risk-manager: fractional Kelly, hard caps, regime auto-pause, daily-DD gate
- ✅ Paper execution + TWAP/VWAP/Iceberg slicing; ccxt live adapter (fail-closed)
- ✅ Strategies: grid, dca, scalping, arbitrage, portfolio(Markowitz), planner
- 🟡 Strategies w/ pluggable feeds: sniper+honeypot, mev(backrun), news-NLP,
      onchain-flow, yield — logic done, real data/RPC wiring pending
- ✅ AI brain: predictor interface + momentum baseline + AutoML scaffold
- ✅ Backtester + Monte Carlo go-live gate
- ✅ Telegram commander (whitelist + TOTP 2FA + degen confirmation)
- ✅ FastAPI + Plotly dashboard
- ✅ Persistence: TimescaleDB schema + JSONL fallback
- ✅ Docker Compose stack, docs, tests, CI
- ✅ **User-configurable strategy** (no code): risk-profile rosters +
      persistent JSON config (`data/strategy_config.json`) + live Telegram
      control (`/strategies`, `/set_param`, `/params`, `/symbols`). See
      `docs/CONFIGURATION.md`.

## Phase 1 — Real connectivity 🟡 (in progress)
- ✅ ccxt.pro L2 order-book websocket source (`data/sources/orderbook_ws.py`),
      auto-preferred when keys exist; feeds scalping real OBI
- ✅ Execution **adapter layer** (`execution/adapters/`) + smart routing
      (`best_venue`) + fail-closed gateway refactor
- ✅ Honeypot screener wired to free **GoPlus** API (pure parser + tests)
- ✅ **DefiLlama** yields feed (`data/sources/defi_yields.py` + `data/feeds.py`)
- 🟡 DEX execution adapters: EVM (web3.py) + Solana/Jupiter — structured
      scaffolds, inert until RPC + hot-wallet wired (safety steps documented)
- ⬜ Real sentiment crawlers (X/Twitter, Telegram callers, Reddit) → NEWS
      (needs API tokens — pending user secrets)
- ✅ Derivatives/flow feed from **public** Binance Futures (funding rate, open
      interest, CVD from aggTrades) → 'onchain' items, no key required
- ✅ New-pool detector via **public** DexScreener API → 'new_pool' items
      (sniper screens each via GoPlus before any buy)
- ⬜ True on-chain stablecoin netflow (needs a data provider/API)

## Phase 2 — Intelligence 🟡 (in progress)
- ✅ Feature engineering (`ai/features.py`): scale-free multi-horizon features +
      forward-return labels, no train/serve skew
- ✅ Trainable predictor behind `Predictor` (`ai/models.py`: GradientBoosting/
      XGBoost) with momentum fallback; LSTM/Transformer drop-in ready
- ✅ Real AutoML with **walk-forward** out-of-sample selection (`ai/automl.py`),
      wired into the ai-brain service (periodic retrain + select)
- ✅ Correlation exposure model (`risk/correlation.py`) wired into risk-manager
      (caps co-moving clusters; inverse-correlated hedges not penalised)
- ✅ LLM-assisted symbolic planner (`ai/llm_planner.py`): proposes **sandboxed,
      validated** rules from live facts; wired into ai-brain -> planner. Safe by
      construction (data not code, leverage/size clamped, always sandboxed).
      No-op without `ANTHROPIC_API_KEY` + `pip install anthropic`.
- ⬜ Sector/category exposure map (static taxonomy) on top of correlation
- ⬜ torch LSTM/Transformer predictor implementation (GPU optional)

## Phase 3 — Scale & ops 🟡 (in progress)
- ✅ Prometheus-compatible `/metrics` (`apex/obs/metrics.py`, no deps) + bus-driven
      collector (`apex/obs/collector.py`); Prometheus+Grafana opt-in compose
      profile (`deploy/prometheus.yml`)
- ✅ Auto-recovery retry/backoff utility (`apex/obs/retry.py`, sync + async) +
      resilient HTTP (`apex/obs/http.py`) wired into ALL public sources (GoPlus,
      DefiLlama, DexScreener, Binance public)
- ✅ Multi-exchange failover (`apex/execution/circuit.py`): per-venue circuit
      breakers + auto-migrate the pair to a healthy venue on outage (fail-closed)
- ✅ Grafana dashboard JSON (pre-built panels) auto-provisioned + Prometheus
      datasource (`deploy/grafana/`)
- ⬜ Alert rules (Prometheus/Grafana) for drawdown/pause/no-fills
- ⬜ gRPC for hot-path service calls alongside Pub/Sub (per spec)
- ⬜ Multichain bridge router (cheapest-chain fund movement)
- ⬜ Backtest data lake + automated nightly strategy re-validation

## Phase 4 — Advanced (gated, high-risk) ⬜
- ⬜ Perp leverage execution with dynamic hedging (degen profile)
- ⬜ Flash-loan arbitrage with mandatory local-fork simulation pre-send
- ⬜ Options hedging via decentralised derivatives on systemic-risk signal
- ⬜ Risk-filtered copy-trading

## Known limitations / honest notes
- Advanced strategies emit signals but need real data/venue wiring to be useful.
- ML predictors are baseline; no profitable model is shipped (by design).
- Live trading is intentionally hard to enable; that is a feature.
