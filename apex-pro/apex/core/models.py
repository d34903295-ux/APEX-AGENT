"""Domain models shared across every microservice.

Plain dataclasses (no heavy deps) so they can travel over the bus as dicts and
be reconstructed anywhere. Use `.to_dict()` / `.from_dict()` for transport.
"""
from __future__ import annotations

import time
import uuid
from dataclasses import asdict, dataclass, field
from enum import Enum
from typing import Any


def _now() -> float:
    return time.time()


def _id() -> str:
    return uuid.uuid4().hex[:12]


class Side(str, Enum):
    BUY = "buy"
    SELL = "sell"


class OrderType(str, Enum):
    MARKET = "market"
    LIMIT = "limit"


class SignalAction(str, Enum):
    OPEN = "open"
    CLOSE = "close"
    INCREASE = "increase"
    REDUCE = "reduce"
    REBALANCE = "rebalance"


@dataclass
class MarketTick:
    symbol: str
    price: float
    bid: float = 0.0
    ask: float = 0.0
    volume: float = 0.0
    exchange: str = "paper"
    ts: float = field(default_factory=_now)

    @property
    def spread(self) -> float:
        if self.bid and self.ask:
            return (self.ask - self.bid) / self.ask
        return 0.0

    def to_dict(self) -> dict[str, Any]:
        return asdict(self)

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "MarketTick":
        return cls(**d)


@dataclass
class Signal:
    """A trading intent emitted by a strategy. NOT yet authorized to execute."""
    strategy: str
    symbol: str
    side: Side
    action: SignalAction = SignalAction.OPEN
    confidence: float = 0.5          # 0..1, used by Kelly sizing
    target_pct: float | None = None  # desired position size as % of equity
    price_hint: float | None = None
    stop_loss: float | None = None
    take_profit: float | None = None
    leverage: float = 1.0
    exchange: str = "paper"
    rationale: str = ""
    meta: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=_id)
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["side"] = self.side.value
        d["action"] = self.action.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Signal":
        d = dict(d)
        d["side"] = Side(d["side"])
        d["action"] = SignalAction(d.get("action", "open"))
        return cls(**d)


@dataclass
class Order:
    """A risk-approved instruction ready for the execution gateway."""
    symbol: str
    side: Side
    amount: float                 # in base/quote units depending on exchange
    type: OrderType = OrderType.MARKET
    price: float | None = None
    leverage: float = 1.0
    exchange: str = "paper"
    strategy: str = ""
    signal_id: str = ""
    stop_loss: float | None = None
    take_profit: float | None = None
    algo: str | None = None       # twap | vwap | iceberg | None
    meta: dict[str, Any] = field(default_factory=dict)
    id: str = field(default_factory=_id)
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["side"] = self.side.value
        d["type"] = self.type.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Order":
        d = dict(d)
        d["side"] = Side(d["side"])
        d["type"] = OrderType(d.get("type", "market"))
        return cls(**d)


@dataclass
class Fill:
    order_id: str
    symbol: str
    side: Side
    amount: float
    price: float
    fee: float = 0.0
    exchange: str = "paper"
    strategy: str = ""
    ts: float = field(default_factory=_now)

    def to_dict(self) -> dict[str, Any]:
        d = asdict(self)
        d["side"] = self.side.value
        return d

    @classmethod
    def from_dict(cls, d: dict[str, Any]) -> "Fill":
        d = dict(d)
        d["side"] = Side(d["side"])
        return cls(**d)


@dataclass
class Position:
    symbol: str
    amount: float = 0.0           # signed: >0 long, <0 short
    avg_price: float = 0.0
    leverage: float = 1.0
    strategy: str = ""
    stop_loss: float | None = None
    take_profit: float | None = None

    def notional(self, mark: float) -> float:
        return abs(self.amount) * mark

    def unrealized_pnl(self, mark: float) -> float:
        return (mark - self.avg_price) * self.amount
