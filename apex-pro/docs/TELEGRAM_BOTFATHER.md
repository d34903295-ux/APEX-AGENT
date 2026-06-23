# Telegram Commander — BotFather Setup

## 1. Create the bot

1. Open [@BotFather](https://t.me/BotFather) in Telegram.
2. `/newbot` → choose a name and a username ending in `bot`.
3. Copy the **HTTP API token** → put it in `.env` as `TELEGRAM_BOT_TOKEN`.

## 2. Lock it down (whitelist + 2FA)

1. Find your numeric user ID (message [@userinfobot](https://t.me/userinfobot)).
2. `.env`: `TELEGRAM_ALLOWED_USER_IDS=123456789` (comma-separate for several).
3. Generate a base32 2FA secret and add it to an authenticator app:
   ```bash
   python -c "import base64,os;print(base64.b32encode(os.urandom(20)).decode())"
   ```
   Put it in `.env` as `TELEGRAM_2FA_SECRET`, and add the same secret to Google
   Authenticator / Aegis (manual entry, type: time-based).

> The bot **fails closed**: with no whitelist configured, it rejects everyone.

## 3. Register the command menu (paste into BotFather `/setcommands`)

```
start - Welcome & authorisation check
status - Agent mode, profile, paused state, strategies
balance - Portfolio snapshot (cash, equity, positions)
performance - Realised PnL, fees, drawdown
pause - Halt all trading immediately
resume - Resume trading
set_strategy - Enable/disable a strategy live: /set_strategy on|off <name>
risk_profile - Set risk: conservative|balanced|aggressive|degen
force_trade - Manual override (needs 2FA): /force_trade buy|sell SYM pct
withdraw - Withdrawal intent (needs 2FA + allow-list)
deposit_address - Show deposit address for a chain/asset
log - Recent alerts & risk events
2fa - Unlock dangerous ops for 5 min: /2fa <code>
```

## 4. Suggested bot description / "system prompt" (BotFather `/setdescription`)

> 🦾 APEX-AGENT PRO — your autonomous multi-asset trading agent. I analyse
> markets 24/7, manage risk with hard caps and auto-pause, and execute across
> CeFi & DeFi. I run in PAPER mode until you explicitly enable live trading.
> Use /status and /balance any time; /pause stops me instantly. Dangerous
> actions require 2FA (/2fa <code>). I will never ask for your private keys.

And `/setabouttext`:

> Autonomous trading agent. Paper-first, risk-capped, stoppable with /pause.

## 5. Dangerous-action flow (built-in)

- Enabling **degen** or **live**, **withdraw**, **force_trade** all require a
  fresh 2FA unlock: send `/2fa <code>` (valid 5 min), then the command.
- `degen` additionally requires a typed confirmation:
  `/risk_profile degen CONFIRM`.

## 6. Proactive alerts

The bot pushes messages to every whitelisted ID on: trade open/close, risk
auto-pause, abnormal regime, detected opportunities, and critical errors.
