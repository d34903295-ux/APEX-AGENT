# Architecture — APEX-AGENT PRO

## Principles
- **Event-driven & decoupled.** Services only know the bus and the shared
  domain models. Same code runs single-process or as containers.
- **Safety as a first-class component.** The risk-manager is a mandatory gate;
  nothing reaches an exchange without passing it.
- **Batteries-included, dependency-light core.** The engine runs with just
  `python-dotenv`+`rich`; everything heavy (ccxt, ML, web3, redis) is optional
  and lazily imported.
- **Hot-swappable plugins.** Strategies self-register and can be toggled live.

## Services
| Service | Entrypoint | Subscribes | Publishes |
|---|---|---|---|
| data-feeder | `apex.services.data_feeder` | — | `ticks`, `news` |
| strategy-engine | `apex.services.strategy_engine` | `ticks`,`news`,`predictions`,`commands` | `signals` |
| risk-manager | `apex.services.risk_manager` | `signals`,`ticks`,`fills`,`commands` | `orders`,`risk`,`alerts` |
| execution-gateway | `apex.services.execution_gateway` | `orders`,`ticks` | `fills`,`alerts` |
| ai-brain | `apex.services.ai_brain` | `ticks` | `predictions` |
| telegram-commander | `apex.services.telegram_commander` | `alerts`,`heartbeat` | `commands` |
| dashboard | `apex.dashboard.app` | `heartbeat`,`alerts` | — |

Channels are defined in `apex/bus/events.py`.

## Data flow (one trade)
1. `data-feeder` publishes a `MarketTick`.
2. `strategy-engine` routes it to each enabled `Strategy.on_tick` → `Signal`s.
3. `risk-manager.evaluate(signal)` sizes (Kelly), checks caps/regime/pause →
   `Order` (or rejection on `risk`).
4. `execution-gateway` executes (paper or ccxt; slices via TWAP/VWAP/Iceberg) →
   `Fill`.
5. `risk-manager` updates its portfolio mirror from `fills`; `heartbeat`
   broadcasts the snapshot; telegram/dashboard render it.

## Domain models (`apex/core/models.py`)
`MarketTick`, `Signal`, `Order`, `Fill`, `Position` — plain dataclasses with
`to_dict`/`from_dict` for transport over the bus.

## Bus (`apex/bus/redis_bus.py`)
`make_bus()` returns a process-wide singleton: `RedisBus` if `REDIS_URL` is set
and reachable, else `InProcessBus` (asyncio queues). Identical async API.

## Risk (`apex/risk/`)
- `kelly.py` — fractional Kelly sizing.
- `regime.py` — volatility/jump regime detection → auto-pause.
- `montecarlo.py` — drawdown & risk-of-ruin simulation + go-live gate.
- `manager.py` — the gate; sizing, caps, pause/resume, portfolio mirror.

## Execution (`apex/execution/`)
- `paper.py` — default simulated executor (slippage+fee model).
- `algos.py` — TWAP / VWAP / Iceberg order slicing (pure generators).
- `gateway.py` — routing; fail-closed to paper; ccxt adapter; DEX adapters TBD.

## AI (`apex/ai/brain.py`)
`Predictor` interface; `MomentumPredictor` baseline (no deps);
`MLPredictor` (sklearn/xgboost); `AutoML.select()` promotes best model. Plug
torch LSTM/Transformer behind the same interface.

## Persistence (`apex/persistence/`)
`get_recorder()` → `SqlRecorder` (TimescaleDB/Postgres, schema in `schema.sql`)
or `JsonlRecorder` fallback (append-only audit). Immutable decision log.

## Extending
- **New strategy:** subclass `Strategy`, decorate with
  `@STRATEGY_REGISTRY.register("name")`, add to `strategies/__init__.py`.
- **New data source:** implement `async def stream() -> AsyncIterator[...]` and
  publish to `ticks`/`news`.
- **New venue:** add a branch in `execution/gateway.py` (CEX via ccxt is
  generic; DEX needs a web3/jupiter adapter).
