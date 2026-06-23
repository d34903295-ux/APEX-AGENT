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
- ✅ Docker Compose stack, docs, tests (18+ passing), CI

## Phase 1 — Real connectivity 🟡
- ⬜ ccxt.pro websockets for low-latency L2 order books (replace REST poll)
- ⬜ Wire honeypot screener to RPC sell-simulation + GoPlus/Honeypot.is
- ⬜ DEX execution adapters: Uniswap (web3.py) + Jupiter (solana.py)
- ⬜ Real sentiment crawlers (X/Twitter, Telegram callers, Reddit) → NEWS
- ⬜ On-chain feeds: exchange netflows, CVD, perp OI/funding aggregator
- ⬜ DeFi yields feed (DefiLlama) for the yield strategy

## Phase 2 — Intelligence ⬜
- ⬜ Feature store + XGBoost/LSTM/Transformer predictors behind `Predictor`
- ⬜ Real AutoML weekly model selection with walk-forward validation
- ⬜ LLM-assisted symbolic planner proposing sandboxed rules from regime
- ⬜ Correlation/sector exposure model feeding the risk-manager

## Phase 3 — Scale & ops ⬜
- ⬜ gRPC for hot-path service calls alongside Pub/Sub (per spec)
- ⬜ Multichain bridge router (cheapest-chain fund movement)
- ⬜ Prometheus/Grafana metrics + alerting; structured tracing
- ⬜ Backtest data lake + automated nightly strategy re-validation
- ⬜ Multi-exchange failover (auto-migrate pair on venue outage)

## Phase 4 — Advanced (gated, high-risk) ⬜
- ⬜ Perp leverage execution with dynamic hedging (degen profile)
- ⬜ Flash-loan arbitrage with mandatory local-fork simulation pre-send
- ⬜ Options hedging via decentralised derivatives on systemic-risk signal
- ⬜ Risk-filtered copy-trading

## Known limitations / honest notes
- Advanced strategies emit signals but need real data/venue wiring to be useful.
- ML predictors are baseline; no profitable model is shipped (by design).
- Live trading is intentionally hard to enable; that is a feature.
