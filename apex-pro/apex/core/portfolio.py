"""In-memory portfolio accounting shared by the paper executor and risk-manager.

Tracks cash, positions, realised/unrealised PnL and equity. Thread-unsafe by
design — drive it from a single asyncio loop (the execution-gateway owns it and
publishes snapshots on the bus).
"""
from __future__ import annotations

from dataclasses import dataclass, field

from apex.core.models import Fill, Position, Side


@dataclass
class Portfolio:
    base_currency: str = "USDT"
    cash: float = 10_000.0
    positions: dict[str, Position] = field(default_factory=dict)
    realized_pnl: float = 0.0
    fees_paid: float = 0.0
    _marks: dict[str, float] = field(default_factory=dict)
    _peak_equity: float = 0.0

    def mark(self, symbol: str, price: float) -> None:
        self._marks[symbol] = price
        self._peak_equity = max(self._peak_equity, self.total_equity())

    # NOTE: we use simple cash accounting — buying reduces cash, selling adds it.
    def apply_fill(self, fill: Fill) -> None:
        pos = self.positions.get(fill.symbol, Position(symbol=fill.symbol, strategy=fill.strategy))
        signed = fill.amount if fill.side is Side.BUY else -fill.amount
        cost = fill.price * fill.amount
        self.cash -= cost if fill.side is Side.BUY else -cost
        self.cash -= fill.fee
        self.fees_paid += fill.fee

        new_amount = pos.amount + signed
        if pos.amount == 0 or (pos.amount > 0) == (signed > 0):
            # opening / increasing in same direction -> weighted avg price
            total = abs(pos.amount) + abs(signed)
            if total > 0:
                pos.avg_price = (pos.avg_price * abs(pos.amount) + fill.price * abs(signed)) / total
        else:
            # reducing / closing -> realise PnL on the reduced quantity
            closed = min(abs(signed), abs(pos.amount))
            direction = 1 if pos.amount > 0 else -1
            self.realized_pnl += (fill.price - pos.avg_price) * closed * direction
        pos.amount = new_amount
        if abs(pos.amount) < 1e-12:
            self.positions.pop(fill.symbol, None)
        else:
            self.positions[fill.symbol] = pos
        self._peak_equity = max(self._peak_equity, self.total_equity())

    def total_equity(self) -> float:
        unreal = sum(
            p.unrealized_pnl(self._marks.get(sym, p.avg_price))
            for sym, p in self.positions.items()
        )
        invested = sum(abs(p.amount) * p.avg_price for p in self.positions.values())
        return self.cash + invested + unreal

    def drawdown(self) -> float:
        if self._peak_equity <= 0:
            return 0.0
        return max(0.0, (self._peak_equity - self.total_equity()) / self._peak_equity)

    def exposure_pct(self, symbol: str) -> float:
        eq = self.total_equity() or 1.0
        pos = self.positions.get(symbol)
        if not pos:
            return 0.0
        mark = self._marks.get(symbol, pos.avg_price)
        return pos.notional(mark) / eq

    def snapshot(self) -> dict:
        return {
            "cash": round(self.cash, 2),
            "equity": round(self.total_equity(), 2),
            "realized_pnl": round(self.realized_pnl, 2),
            "fees_paid": round(self.fees_paid, 2),
            "drawdown": round(self.drawdown(), 4),
            "positions": {
                sym: {
                    "amount": p.amount, "avg_price": p.avg_price,
                    "mark": self._marks.get(sym, p.avg_price),
                    "upnl": round(p.unrealized_pnl(self._marks.get(sym, p.avg_price)), 2),
                }
                for sym, p in self.positions.items()
            },
        }
