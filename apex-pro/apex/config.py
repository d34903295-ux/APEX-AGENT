"""Central configuration for APEX-AGENT PRO.

Loads from environment (.env via python-dotenv if present). Everything has a
*safe* default: the agent boots in PAPER mode with a CONSERVATIVE risk profile
and live trading disabled. You must explicitly opt in to anything dangerous.
"""
from __future__ import annotations

import os
from dataclasses import dataclass, field
from enum import Enum
from functools import lru_cache

try:  # optional, but recommended
    from dotenv import load_dotenv

    load_dotenv()
except Exception:  # pragma: no cover - dotenv is optional
    pass


def _b(key: str, default: bool) -> bool:
    return os.getenv(key, str(default)).strip().lower() in {"1", "true", "yes", "on"}


def _f(key: str, default: float) -> float:
    try:
        return float(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


def _i(key: str, default: int) -> int:
    try:
        return int(os.getenv(key, default))
    except (TypeError, ValueError):
        return default


class TradingMode(str, Enum):
    PAPER = "paper"
    LIVE = "live"


class RiskProfile(str, Enum):
    CONSERVATIVE = "conservative"
    BALANCED = "balanced"
    AGGRESSIVE = "aggressive"
    DEGEN = "degen"


@dataclass(frozen=True)
class RiskLimits:
    max_position_pct: float = _f("APEX_MAX_POSITION_PCT", 0.10)
    max_portfolio_leverage: float = _f("APEX_MAX_PORTFOLIO_LEVERAGE", 1.0)
    max_daily_drawdown_pct: float = _f("APEX_MAX_DAILY_DRAWDOWN_PCT", 0.05)
    max_degen_leverage: float = _f("APEX_MAX_DEGEN_LEVERAGE", 100.0)
    max_open_positions: int = _i("APEX_MAX_OPEN_POSITIONS", 8)
    max_correlated_exposure_pct: float = _f("APEX_MAX_CORRELATED_EXPOSURE_PCT", 0.30)

    def for_profile(self, profile: RiskProfile) -> "RiskLimits":
        """Profiles scale the *defaults*. Degen unlocks leverage but is still capped."""
        if profile is RiskProfile.CONSERVATIVE:
            return self
        if profile is RiskProfile.BALANCED:
            return RiskLimits(
                max_position_pct=min(0.15, self.max_position_pct * 1.5),
                max_portfolio_leverage=max(2.0, self.max_portfolio_leverage),
                max_daily_drawdown_pct=0.08,
                max_open_positions=12,
            )
        if profile is RiskProfile.AGGRESSIVE:
            return RiskLimits(
                max_position_pct=0.25,
                max_portfolio_leverage=5.0,
                max_daily_drawdown_pct=0.15,
                max_open_positions=20,
            )
        # DEGEN — extreme, but still bounded by an absolute hard cap.
        return RiskLimits(
            max_position_pct=0.40,
            max_portfolio_leverage=self.max_degen_leverage,
            max_daily_drawdown_pct=0.40,
            max_open_positions=40,
        )


@dataclass(frozen=True)
class Settings:
    mode: TradingMode = TradingMode(os.getenv("APEX_MODE", "paper").lower())
    risk_profile: RiskProfile = RiskProfile(os.getenv("APEX_RISK_PROFILE", "conservative").lower())
    live_trading_enabled: bool = _b("APEX_LIVE_TRADING_ENABLED", False)
    degen_requires_confirmation: bool = _b("APEX_DEGEN_REQUIRES_CONFIRMATION", True)
    enable_council: bool = _b("APEX_ENABLE_COUNCIL", False)
    base_currency: str = os.getenv("APEX_BASE_CURRENCY", "USDT")
    paper_balance: float = _f("APEX_PAPER_BALANCE", 10_000.0)

    redis_url: str = os.getenv("REDIS_URL", "")
    database_url: str = os.getenv("DATABASE_URL", "")
    sqlite_cache_path: str = os.getenv("SQLITE_CACHE_PATH", "./data/apex_cache.db")

    telegram_token: str = os.getenv("TELEGRAM_BOT_TOKEN", "")
    telegram_allowed_ids: tuple[int, ...] = field(default_factory=lambda: tuple(
        int(x) for x in os.getenv("TELEGRAM_ALLOWED_USER_IDS", "").replace(" ", "").split(",") if x
    ))
    telegram_2fa_secret: str = os.getenv("TELEGRAM_2FA_SECRET", "")

    dashboard_host: str = os.getenv("DASHBOARD_HOST", "0.0.0.0")
    dashboard_port: int = _i("DASHBOARD_PORT", 8000)

    llm_model: str = os.getenv("APEX_LLM_MODEL", "claude-opus-4-8")
    anthropic_api_key: str = os.getenv("ANTHROPIC_API_KEY", "")

    limits: RiskLimits = field(default_factory=RiskLimits)

    @property
    def effective_limits(self) -> RiskLimits:
        return self.limits.for_profile(self.risk_profile)

    @property
    def is_live(self) -> bool:
        """Live orders require BOTH live mode AND the master kill-switch ON."""
        return self.mode is TradingMode.LIVE and self.live_trading_enabled

    def exchange_credentials(self, exchange: str) -> dict[str, str]:
        ex = exchange.upper()
        creds = {
            "apiKey": os.getenv(f"{ex}_API_KEY", ""),
            "secret": os.getenv(f"{ex}_API_SECRET", ""),
        }
        passphrase = os.getenv(f"{ex}_API_PASSPHRASE", "")
        if passphrase:
            creds["password"] = passphrase
        return creds


@lru_cache(maxsize=1)
def get_settings() -> Settings:
    return Settings()
