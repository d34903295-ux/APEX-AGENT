"""Paper (simulated) execution engine — the DEFAULT and the safety net.

Fills orders against the latest mark with a configurable slippage + fee model.
This is what runs until you *explicitly* enable live trading, and it's also the
engine used for the mandatory 24h forward-test of every new strategy.
"""
from __future__ import annotations

from apex.core.logging import get_logger
from apex.core.models import Fill, Order, Side

log = get_logger("apex.exec.paper")


class PaperExecutor:
    def __init__(self, taker_fee: float = 0.001, slippage: float = 0.0005):
        self.taker_fee = taker_fee
        self.slippage = slippage
        self._marks: dict[str, float] = {}

    def update_mark(self, symbol: str, price: float) -> None:
        self._marks[symbol] = price

    def execute(self, order: Order) -> Fill | None:
        price = order.price or self._marks.get(order.symbol)
        if not price or price <= 0:
            log.warning("paper: no price for %s, dropping order", order.symbol)
            return None
        # Slippage pushes price against us.
        if order.side is Side.BUY:
            fill_price = price * (1 + self.slippage)
        else:
            fill_price = price * (1 - self.slippage)
        fee = fill_price * order.amount * self.taker_fee
        fill = Fill(
            order_id=order.id, symbol=order.symbol, side=order.side,
            amount=order.amount, price=fill_price, fee=fee,
            exchange="paper", strategy=order.strategy,
        )
        log.info("[cyan]PAPER FILL[/cyan] %s %s %.6f @ %.4f (fee %.4f)",
                 order.side.value, order.symbol, order.amount, fill_price, fee)
        return fill
