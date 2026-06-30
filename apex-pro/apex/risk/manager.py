"""Risk-manager: the mandatory gate between every Signal and every Order.

NO order reaches an exchange without passing through here. It:
  * sizes positions with fractional Kelly, clamped to profile hard-caps
  * enforces per-position, leverage, open-position and drawdown limits
  * detects abnormal regimes and AUTO-PAUSES the whole agent
  * blocks sandboxed planner rules from using real capital
  * can be paused/resumed via the COMMANDS channel (Telegram)

It keeps a private mirror of the portfolio by listening to FILLS + TICKS, so it
works identically in single-process and distributed deployments.
"""
from __future__ import annotations

from apex.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.core.models import Fill, Order, OrderType, Signal
from apex.core.portfolio import Portfolio
from apex.risk.correlation import CorrelationTracker
from apex.risk.kelly import sized_position_pct
from apex.risk.regime import Regime, RegimeDetector

log = get_logger("apex.risk")


class RiskManager:
    def __init__(self, settings: Settings | None = None, portfolio: Portfolio | None = None):
        self.s = settings or get_settings()
        limits = self.s.effective_limits
        self.limits = limits
        self.pf = portfolio or Portfolio(
            base_currency=self.s.base_currency, cash=self.s.paper_balance
        )
        self.regime = RegimeDetector()
        self.correlation = CorrelationTracker()
        self.paused = False
        self.pause_reason = ""
        self._day_start_equity = self.pf.total_equity()

    # ---- mutation from the bus ------------------------------------------
    def on_fill(self, fill: Fill) -> None:
        self.pf.apply_fill(fill)

    def on_tick_price(self, symbol: str, price: float) -> list[str]:
        """Update marks + regime. Returns risk-event messages to broadcast."""
        self.pf.mark(symbol, price)
        self.correlation.update(symbol, price)
        events: list[str] = []
        regime = self.regime.update(symbol, price)
        if regime is Regime.ABNORMAL and not self.paused:
            self.pause(f"abnormal regime on {symbol}")
            events.append(f"AUTO-PAUSE: abnormal regime detected on {symbol}")

        dd = self._daily_drawdown()
        if dd > self.limits.max_daily_drawdown_pct and not self.paused:
            self.pause(f"daily drawdown {dd:.2%} exceeded cap")
            events.append(f"AUTO-PAUSE: daily drawdown {dd:.2%} > {self.limits.max_daily_drawdown_pct:.2%}")
        return events

    def _daily_drawdown(self) -> float:
        if self._day_start_equity <= 0:
            return 0.0
        return max(0.0, (self._day_start_equity - self.pf.total_equity()) / self._day_start_equity)

    # ---- control --------------------------------------------------------
    def pause(self, reason: str = "manual") -> None:
        self.paused = True
        self.pause_reason = reason
        log.warning("[red]RISK PAUSE[/red]: %s", reason)

    def resume(self) -> None:
        self.paused = False
        self.pause_reason = ""
        self._day_start_equity = self.pf.total_equity()
        log.info("[green]RISK RESUME[/green]")

    def set_profile(self, name: str) -> bool:
        """Change the active risk profile at runtime (limits take effect on the
        next evaluate()). Returns False for an unknown profile."""
        from apex.config import RiskProfile

        try:
            profile = RiskProfile(name.lower())
        except ValueError:
            log.warning("unknown risk profile %r", name)
            return False
        self.profile = profile
        self.limits = self.s.limits.for_profile(profile)
        log.info("[cyan]risk profile -> %s[/cyan] (max_lev=%sx max_pos=%.0f%%)",
                 profile.value, self.limits.max_portfolio_leverage,
                 self.limits.max_position_pct * 100)
        return True

    # ---- the gate -------------------------------------------------------
    def evaluate(self, signal: Signal) -> tuple[Order | None, str]:
        """Return (Order, reason) — Order is None when rejected."""
        if self.paused:
            return None, f"paused: {self.pause_reason}"

        # Sandboxed planner rules may NEVER use real capital.
        if signal.meta.get("sandboxed") and self.s.is_live:
            return None, "sandboxed rule blocked from live capital"

        # Leverage cap (profile-aware; degen unlocks but is still bounded).
        if signal.leverage > self.limits.max_portfolio_leverage:
            return None, (
                f"leverage {signal.leverage}x > cap {self.limits.max_portfolio_leverage}x"
            )

        if len(self.pf.positions) >= self.limits.max_open_positions \
                and signal.symbol not in self.pf.positions:
            return None, "max open positions reached"

        # Size the position: explicit target, else Kelly from confidence.
        size_pct = signal.target_pct
        if size_pct is None:
            size_pct = sized_position_pct(
                signal.confidence, hard_cap=self.limits.max_position_pct
            )
        size_pct = min(size_pct, self.limits.max_position_pct)
        if size_pct <= 0:
            return None, "sized to zero"

        # Existing exposure check.
        current = self.pf.exposure_pct(signal.symbol)
        if current + size_pct > self.limits.max_position_pct * 1.5:
            return None, f"exposure cap on {signal.symbol}"

        # Correlated-cluster exposure: a new position plus everything it's
        # highly correlated with must stay under the correlation cap.
        correlated = self.correlation.correlated_symbols(
            signal.symbol, list(self.pf.positions)
        )
        cluster_exposure = current + size_pct + sum(
            self.pf.exposure_pct(c) for c in correlated
        )
        if cluster_exposure > self.limits.max_correlated_exposure_pct:
            return None, (
                f"correlated exposure {cluster_exposure:.0%} > cap "
                f"{self.limits.max_correlated_exposure_pct:.0%} "
                f"(cluster: {[signal.symbol, *correlated]})"
            )

        price = signal.price_hint or self.pf._marks.get(signal.symbol)
        if not price or price <= 0:
            return None, "no price available"

        equity = self.pf.total_equity()
        notional = equity * size_pct * max(1.0, signal.leverage)
        amount = notional / price

        order = Order(
            symbol=signal.symbol, side=signal.side, amount=amount,
            type=OrderType.MARKET if signal.price_hint is None else OrderType.LIMIT,
            price=signal.price_hint, leverage=signal.leverage,
            exchange=signal.exchange, strategy=signal.strategy, signal_id=signal.id,
            stop_loss=signal.stop_loss, take_profit=signal.take_profit,
            algo=signal.meta.get("algo"), meta={"size_pct": size_pct},
        )
        return order, "approved"
