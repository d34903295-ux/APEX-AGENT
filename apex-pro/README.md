# APEX-AGENT PRO 🦾📈

> Autonomous, multi-asset (CeFi + DeFi) investment agent. Event-driven
> microservices, controllable end-to-end from Telegram, **paper-first** by
> design. Clone → configure → running in ~30 minutes.

This is the **Python autonomous backend** that evolves the original
[`APEX-AGENT`](../README.md) React copilot into a self-operating trading agent:
it *thinks, analyses, decides and learns* on a continuous loop, while remaining
stoppable from your phone at any moment.

> [!WARNING]
> **Trading risk.** Algorithmic trading — especially with leverage — can lose
> **all** of your capital, fast. This software is provided for research and
> educational use. It ships in **paper (simulated) mode** and refuses to send a
> single real order until you flip multiple explicit safety switches. You are
> solely responsible for any live use. Read [`docs/RISK_DISCLAIMER.md`](docs/RISK_DISCLAIMER.md).
> APEX implements only **legitimate** strategies — see the ethics notes in
> `apex/strategies/mev.py` and `apex/strategies/news_nlp.py`.

---

## 30-second quickstart (zero infrastructure)

```bash
cd apex-pro
python -m venv .venv && source .venv/bin/activate
pip install python-dotenv rich            # minimal core
python -m apex.main                        # runs in PAPER mode on synthetic data
```

You'll see strategies enable, a synthetic market feed start, and `PAPER FILL`
lines as the agent trades against itself. No keys, no Redis, no DB required —
the bus and data feed fall back to in-process implementations.

Full install + Telegram + dashboard:

```bash
pip install -r requirements.txt
cp .env.example .env        # add TELEGRAM_BOT_TOKEN + TELEGRAM_ALLOWED_USER_IDS
python -m apex.main
```

Distributed (Docker, Redis + TimescaleDB + all services):

```bash
cp .env.example .env
docker compose up -d --build
```

---

## What it does (capability map)

| Area | Module | Status |
|---|---|---|
| **Strategy engine (hot-swap)** | `apex/strategies/` + `engine.py` | ✅ functional core |
| Dynamic grid / smart DCA / scalping (microstructure) | `grid.py` `dca.py` `scalping.py` | ✅ functional |
| Cross-exchange & triangular arbitrage (fee+slippage aware) | `arbitrage.py` | ✅ functional |
| DEX sniper + honeypot/rug screener (capital protection) | `sniper.py` `honeypot.py` | ✅ logic, RPC probes stubbed |
| MEV — **backrun-arb & liquidations only** (no sandwich) | `mev.py` | ✅ logic, bundle exec stubbed |
| News/social NLP **with pump&dump defense** | `news_nlp.py` | ✅ logic, feeds pluggable |
| On-chain flow (whales/CVD/OI/netflow) | `onchain_flow.py` | ✅ logic, feeds pluggable |
| Yield farming rotation (audited-protocol allow-list) | `yield_farming.py` | ✅ logic |
| Markowitz / max-Sharpe rebalance | `portfolio.py` | ✅ functional |
| **Symbolic micro-strategy planner** (creativity) | `planner.py` | ✅ functional |
| **Risk manager** (Kelly sizing, caps, regime auto-pause) | `apex/risk/` | ✅ functional |
| Monte Carlo drawdown / risk-of-ruin gate | `risk/montecarlo.py` | ✅ functional |
| **Execution** (paper, smart-route, TWAP/VWAP/Iceberg) | `apex/execution/` | ✅ paper functional, live via ccxt |
| **AI brain** (predictors + AutoML, LSTM/XGB pluggable) | `apex/ai/brain.py` | ✅ baseline + interfaces |
| **Telegram commander** (whitelist + TOTP 2FA) | `apex/telegram/` | ✅ functional |
| Real-time dashboard (FastAPI + Plotly) | `apex/dashboard/` | ✅ functional |
| Backtest + 24h forward-test gate | `apex/backtest/` | ✅ functional |
| Immutable audit log (Timescale/Postgres, JSONL fallback) | `apex/persistence/` | ✅ functional |
| Redis Pub/Sub bus (in-proc fallback) | `apex/bus/` | ✅ functional |

> **"Functional core, extensible everywhere."** The skeleton runs end-to-end in
> paper mode today; advanced modules expose clean interfaces and clearly-marked
> stubs (`screen_token`, live MEV bundle submission, social crawlers) so an
> intermediate dev can wire real data sources/venues incrementally.

---

## Architecture

```
                 ┌────────────┐   ticks    ┌──────────────────┐
   exchanges ───▶│ data-feeder│──────────▶ │  strategy-engine │──┐ signals
   chains/news   └────────────┘   news/    │ (hot-swap plugins)│  │
                                  preds     └──────────────────┘  ▼
   ┌─────────────┐   predictions      ▲        ┌───────────────────────┐
   │  ai-brain   │────────────────────┘        │      risk-manager     │
   │ (ML/AutoML) │                             │ Kelly · caps · regime │
   └─────────────┘                             │ auto-pause · MonteCarlo│
        ▲ ticks                                └───────────┬───────────┘
        │                                          orders  │ (approved only)
        │                                                  ▼
   ┌────┴───────┐   alerts/heartbeat        ┌───────────────────────────┐
   │  telegram  │◀──────────────────────────│     execution-gateway     │
   │  commander │   commands ──────────────▶│ paper · ccxt · TWAP/VWAP  │
   └────────────┘                           └───────────┬───────────────┘
        ▲                                         fills  │
        │            ┌───────────┐                       ▼
        └────────────│ dashboard │◀──── heartbeat ── (bus: Redis Pub/Sub
                     └───────────┘                    or in-process)
```

All services are decoupled over the **event bus** (`apex/bus`). Run them in one
process (`python -m apex.main`) or as separate containers — identical code.

See [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) for the full design.

---

## Safety model (why it won't nuke your account)

1. **Paper by default.** `APEX_MODE=paper` and `APEX_LIVE_TRADING_ENABLED=false`.
   Live orders require **both** to be flipped (`Settings.is_live`).
2. **Fail-closed execution.** Any uncertainty in the gateway routes to paper.
3. **Hard risk caps** per position / leverage / open-positions / correlation,
   enforced on every order — even in `degen`, leverage has an absolute ceiling.
4. **Auto-pause** on abnormal volatility regimes or daily-drawdown breach.
5. **New strategies are gated**: backtest → 24h paper forward-test → Monte
   Carlo `safe_to_go_live` check before real capital is allowed.
6. **Dangerous Telegram ops** (go-live, degen, withdraw, force-trade) need a
   fresh **TOTP 2FA** unlock *and* a typed `CONFIRM`.
7. **Secrets** never logged; keys read from env/secret-manager; use a dedicated
   low-balance hot wallet only.

---

## Documentation

- [`docs/CONFIGURATION.md`](docs/CONFIGURATION.md) — **configure your strategy without code** (risk profile, JSON file, or live via Telegram).
- [`docs/DEPLOYMENT.md`](docs/DEPLOYMENT.md) — step-by-step VPS deploy.
- [`docs/TELEGRAM_BOTFATHER.md`](docs/TELEGRAM_BOTFATHER.md) — BotFather setup + system prompt + command list.
- [`docs/TESTING.md`](docs/TESTING.md) — the "don't self-destruct" validation strategy.
- [`docs/ARCHITECTURE.md`](docs/ARCHITECTURE.md) — services, bus, data models.
- [`docs/RISK_DISCLAIMER.md`](docs/RISK_DISCLAIMER.md) — read before going live.
- [`docs/methodology/SUPERPOWERS.md`](docs/methodology/SUPERPOWERS.md) — dev methodology (Superpowers) used to build & extend this.
- [`ROADMAP.md`](ROADMAP.md) — living roadmap.

## Tests

```bash
pip install pytest pytest-asyncio
pytest -q          # 18+ tests: risk caps, Kelly, Monte Carlo, paper, backtest, bus, ethics-guard
```
