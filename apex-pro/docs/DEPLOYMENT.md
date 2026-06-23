# Deployment Guide — APEX-AGENT PRO

Two supported topologies. Start with **A** (single host) and graduate to **B**.

---

## A) Single-host (laptop / small VPS) — ~10 min

```bash
git clone https://github.com/d34903295-ux/APEX-AGENT.git
cd APEX-AGENT/apex-pro

python3.11 -m venv .venv && source .venv/bin/activate
pip install -r requirements.txt

cp .env.example .env
# Edit .env:  TELEGRAM_BOT_TOKEN, TELEGRAM_ALLOWED_USER_IDS, TELEGRAM_2FA_SECRET
#             (leave exchange keys blank to stay in paper mode)

python -m apex.main          # runs all services in one process
```

Optional dashboard (separate terminal):

```bash
uvicorn apex.dashboard.app:app --host 0.0.0.0 --port 8000
# open http://localhost:8000
```

The in-process bus is used automatically when `REDIS_URL` is empty/unreachable.

---

## B) Distributed (production VPS, Ubuntu 22.04) — ~20 min

Prereqs: Docker + Docker Compose plugin.

```bash
sudo apt update && sudo apt install -y docker.io docker-compose-plugin
git clone https://github.com/d34903295-ux/APEX-AGENT.git
cd APEX-AGENT/apex-pro

cp .env.example .env && nano .env      # fill secrets
docker compose up -d --build           # redis + timescaledb + 7 services
docker compose ps
docker compose logs -f --tail=100
```

Services started: `redis`, `db` (TimescaleDB), `data-feeder`,
`strategy-engine`, `risk-manager`, `execution-gateway`, `ai-brain`,
`telegram-commander`, `dashboard` (port 8000).

### Going live (only after validation — see TESTING.md)

In `.env`:

```ini
APEX_MODE=live
APEX_LIVE_TRADING_ENABLED=true        # master kill-switch
BINANCE_API_KEY=...                   # trade-only keys, withdrawals DISABLED
BINANCE_API_SECRET=...
```

Then `docker compose up -d` to recreate with new env. Confirm in Telegram with
`/status` that `live=true`, and keep `/pause` one tap away.

### Security hardening

- Run on a dedicated user; firewall everything except SSH (and 8000 if you
  expose the dashboard — better: keep it on localhost + SSH tunnel).
- Use **trade-only** API keys with withdrawals disabled and IP allow-listing.
- DeFi: a **dedicated hot wallet** with minimal balance; never your main wallet.
- Store secrets in a manager (Docker secrets / Vault / SOPS), not a bare `.env`,
  for real deployments. `.env` is git-ignored.
- Back up the `apex_db` volume (audit trail) regularly.

### Updating

```bash
git pull
docker compose up -d --build
```

### GPU (optional, for torch LSTM/Transformer models)

Install `torch` in `requirements.txt`, use an NVIDIA base image + `--gpus all`,
or run `ai-brain` on a GPU host pointed at the same Redis.
