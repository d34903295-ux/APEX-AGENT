"""Telegram commander — the single control surface for the agent.

Commands:
  /start            welcome + whitelist check
  /status           agent state (mode, profile, paused, strategies)
  /balance          portfolio snapshot (cash, equity, positions)
  /performance      realised PnL, fees, drawdown
  /pause /resume    halt / restart trading
  /set_strategy     enable/disable a strategy in caliente
  /risk_profile     conservative|balanced|aggressive|degen (degen needs 2FA)
  /force_trade      manual override order (needs 2FA)
  /withdraw         withdrawal intent (needs 2FA + confirmation)
  /deposit_address  show deposit address for a chain/asset
  /log              recent risk events / alerts
  /2fa <code>       supply a TOTP code to unlock dangerous ops for 5 min

Proactive alerts (trade open/close, auto-pause, opportunities, errors) are
pushed from the ALERTS channel.

Dangerous operations are gated by: whitelist + a fresh 2FA unlock. Enabling
'degen' or going live ALSO requires an explicit typed confirmation.
"""
from __future__ import annotations

import time

from apex.bus.events import Channels
from apex.bus.redis_bus import make_bus
from apex.config import RiskProfile, get_settings
from apex.core.logging import get_logger
from apex.telegram.auth import is_whitelisted, verify_2fa

log = get_logger("apex.telegram")

_UNLOCK_TTL = 300  # seconds a 2FA unlock stays valid


async def run_bot(rm=None) -> None:
    """Start the bot. `rm` (RiskManager) is optional: when provided (in-process
    orchestrator) we read portfolio directly; otherwise we use cached heartbeat."""
    try:
        from telegram import Update
        from telegram.ext import (Application, CommandHandler, ContextTypes)
    except ImportError:
        log.warning("python-telegram-bot not installed; Telegram disabled")
        return

    s = get_settings()
    bus = await make_bus()
    state = {"heartbeat": {}, "alerts": [], "unlocks": {}}  # chat_id -> unlock_ts

    def unlocked(chat_id: int) -> bool:
        return time.time() - state["unlocks"].get(chat_id, 0) < _UNLOCK_TTL

    def snapshot() -> dict:
        if rm is not None:
            return {"snapshot": rm.pf.snapshot(), "paused": rm.paused,
                    "reason": rm.pause_reason}
        return state["heartbeat"]

    def guard(update) -> bool:
        uid = update.effective_user.id if update.effective_user else 0
        return is_whitelisted(uid)

    # --- command handlers -------------------------------------------------
    async def start(update: "Update", ctx: "ContextTypes.DEFAULT_TYPE"):
        if not guard(update):
            await update.message.reply_text("⛔ Not authorised. Your ID: "
                                            f"{update.effective_user.id}")
            return
        await update.message.reply_text(
            "🚀 *APEX-AGENT PRO*\nControl surface online.\n"
            f"mode=`{s.mode.value}` profile=`{s.risk_profile.value}` "
            f"live=`{s.is_live}`\nUse /status, /balance, /pause, /resume.",
            parse_mode="Markdown")

    async def status(update, ctx):
        if not guard(update):
            return
        snap = snapshot()
        await update.message.reply_text(
            f"📊 mode=`{s.mode.value}` profile=`{s.risk_profile.value}` "
            f"live=`{s.is_live}`\npaused=`{snap.get('paused')}` "
            f"{snap.get('reason','')}", parse_mode="Markdown")

    async def balance(update, ctx):
        if not guard(update):
            return
        snap = snapshot().get("snapshot", {})
        pos = snap.get("positions", {})
        lines = [f"💰 *Equity:* {snap.get('equity','?')} {s.base_currency}",
                 f"Cash: {snap.get('cash','?')}"]
        for sym, p in pos.items():
            lines.append(f"• {sym}: {p['amount']:.4f} @ {p['avg_price']:.2f} "
                         f"(uPnL {p['upnl']})")
        await update.message.reply_text("\n".join(lines), parse_mode="Markdown")

    async def performance(update, ctx):
        if not guard(update):
            return
        snap = snapshot().get("snapshot", {})
        await update.message.reply_text(
            f"📈 realized PnL: {snap.get('realized_pnl','?')}\n"
            f"fees: {snap.get('fees_paid','?')}\n"
            f"drawdown: {float(snap.get('drawdown',0))*100:.2f}%")

    async def pause(update, ctx):
        if not guard(update):
            return
        await bus.publish(Channels.COMMANDS, {"action": "pause", "reason": "telegram"})
        await update.message.reply_text("⏸️ Pause requested.")

    async def resume(update, ctx):
        if not guard(update):
            return
        await bus.publish(Channels.COMMANDS, {"action": "resume"})
        await update.message.reply_text("▶️ Resume requested.")

    async def set_strategy(update, ctx):
        if not guard(update):
            return
        args = ctx.args
        if len(args) < 2 or args[0] not in ("on", "off"):
            await update.message.reply_text("Usage: /set_strategy on|off <name>")
            return
        action = "enable_strategy" if args[0] == "on" else "disable_strategy"
        await bus.publish(Channels.COMMANDS, {"action": action, "name": args[1]})
        await update.message.reply_text(f"🔧 {action} {args[1]} requested.")

    async def two_fa(update, ctx):
        if not guard(update):
            return
        code = ctx.args[0] if ctx.args else ""
        if verify_2fa(code):
            state["unlocks"][update.effective_chat.id] = time.time()
            await update.message.reply_text("🔓 2FA verified (5 min).")
        else:
            await update.message.reply_text("❌ Invalid 2FA code.")

    async def risk_profile(update, ctx):
        if not guard(update):
            return
        if not ctx.args:
            await update.message.reply_text(
                "Usage: /risk_profile conservative|balanced|aggressive|degen")
            return
        target = ctx.args[0].lower()
        if target == RiskProfile.DEGEN.value:
            if not unlocked(update.effective_chat.id):
                await update.message.reply_text(
                    "⚠️ DEGEN mode enables extreme leverage and can lose ALL "
                    "capital. Send /2fa <code> first, then re-send this command "
                    "with the word CONFIRM: `/risk_profile degen CONFIRM`",
                    parse_mode="Markdown")
                return
            if "CONFIRM" not in [a.upper() for a in ctx.args]:
                await update.message.reply_text("Type `/risk_profile degen CONFIRM` to accept the risk.",
                                                parse_mode="Markdown")
                return
        await bus.publish(Channels.COMMANDS, {"action": "set_profile", "profile": target})
        await update.message.reply_text(f"🎚️ risk profile -> {target} requested.")

    async def force_trade(update, ctx):
        if not guard(update):
            return
        if not unlocked(update.effective_chat.id):
            await update.message.reply_text("🔒 Send /2fa <code> first.")
            return
        if len(ctx.args) < 3:
            await update.message.reply_text("Usage: /force_trade buy|sell SYMBOL pct")
            return
        await bus.publish(Channels.COMMANDS, {
            "action": "force_trade", "side": ctx.args[0],
            "symbol": ctx.args[1], "pct": float(ctx.args[2])})
        await update.message.reply_text("⚡ Manual override submitted to risk-manager.")

    async def withdraw(update, ctx):
        if not guard(update):
            return
        if not unlocked(update.effective_chat.id):
            await update.message.reply_text("🔒 Withdrawals require /2fa <code> first.")
            return
        await update.message.reply_text(
            "🏧 Withdrawal flow is intentionally manual-confirm. "
            "Configure the destination allow-list in config before enabling.")

    async def deposit_address(update, ctx):
        if not guard(update):
            return
        await update.message.reply_text(
            "Configure deposit addresses per chain in your secrets manager; "
            "the bot never stores them in plaintext.")

    async def show_log(update, ctx):
        if not guard(update):
            return
        recent = state["alerts"][-10:]
        await update.message.reply_text("🪵 " + ("\n".join(recent) or "no recent alerts"))

    app = Application.builder().token(s.telegram_token).build()
    for cmd, fn in [
        ("start", start), ("status", status), ("balance", balance),
        ("performance", performance), ("pause", pause), ("resume", resume),
        ("set_strategy", set_strategy), ("risk_profile", risk_profile),
        ("force_trade", force_trade), ("withdraw", withdraw),
        ("deposit_address", deposit_address), ("log", show_log), ("2fa", two_fa),
    ]:
        app.add_handler(CommandHandler(cmd, fn))

    # Background consumers: cache heartbeat, push alerts.
    async def consume_bus():
        import asyncio

        async def hb():
            async for msg in bus.subscribe(Channels.HEARTBEAT):
                state["heartbeat"] = msg

        async def alerts():
            async for msg in bus.subscribe(Channels.ALERTS):
                text = msg.get("text", "")
                state["alerts"].append(text)
                for uid in s.telegram_allowed_ids:
                    try:
                        await app.bot.send_message(uid, text)
                    except Exception:  # pragma: no cover
                        pass

        await asyncio.gather(hb(), alerts())

    log.info("Telegram commander starting")
    async with app:
        await app.start()
        await app.updater.start_polling()
        await consume_bus()
