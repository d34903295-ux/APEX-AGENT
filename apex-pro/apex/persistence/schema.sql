-- APEX-AGENT PRO — persistence schema (PostgreSQL / TimescaleDB)
-- Immutable audit trail: every signal, order, fill and decision is recorded.

CREATE TABLE IF NOT EXISTS ticks (
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol      TEXT NOT NULL,
    exchange    TEXT NOT NULL,
    price       DOUBLE PRECISION NOT NULL,
    bid         DOUBLE PRECISION,
    ask         DOUBLE PRECISION,
    volume      DOUBLE PRECISION
);
-- TimescaleDB hypertable (no-op if extension absent):
-- SELECT create_hypertable('ticks', 'ts', if_not_exists => TRUE);

CREATE TABLE IF NOT EXISTS signals (
    id          TEXT PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    strategy    TEXT NOT NULL,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,
    action      TEXT NOT NULL,
    confidence  DOUBLE PRECISION,
    rationale   TEXT,
    meta        JSONB
);

CREATE TABLE IF NOT EXISTS orders (
    id          TEXT PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    signal_id   TEXT REFERENCES signals(id),
    strategy    TEXT,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,
    amount      DOUBLE PRECISION NOT NULL,
    price       DOUBLE PRECISION,
    leverage    DOUBLE PRECISION,
    exchange    TEXT,
    status      TEXT DEFAULT 'created',
    meta        JSONB
);

CREATE TABLE IF NOT EXISTS fills (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    order_id    TEXT,
    strategy    TEXT,
    symbol      TEXT NOT NULL,
    side        TEXT NOT NULL,
    amount      DOUBLE PRECISION NOT NULL,
    price       DOUBLE PRECISION NOT NULL,
    fee         DOUBLE PRECISION,
    exchange    TEXT
);

CREATE TABLE IF NOT EXISTS risk_events (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    type        TEXT NOT NULL,
    symbol      TEXT,
    reason      TEXT,
    meta        JSONB
);

CREATE TABLE IF NOT EXISTS predictions (
    id          BIGSERIAL PRIMARY KEY,
    ts          TIMESTAMPTZ NOT NULL DEFAULT now(),
    symbol      TEXT NOT NULL,
    model       TEXT,
    direction   DOUBLE PRECISION,
    confidence  DOUBLE PRECISION,
    features    JSONB
);

CREATE INDEX IF NOT EXISTS idx_fills_symbol_ts ON fills(symbol, ts DESC);
CREATE INDEX IF NOT EXISTS idx_signals_strategy_ts ON signals(strategy, ts DESC);
