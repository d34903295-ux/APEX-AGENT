from __future__ import annotations

from apex.core.models import Order, OrderType, Side
from apex.core.portfolio import Portfolio
from apex.execution.paper import PaperExecutor


def test_paper_fill_and_accounting():
    pf = Portfolio(cash=10_000.0)
    ex = PaperExecutor(taker_fee=0.001, slippage=0.0)
    ex.update_mark("BTC/USDT", 100.0)
    pf.mark("BTC/USDT", 100.0)

    order = Order(symbol="BTC/USDT", side=Side.BUY, amount=10, type=OrderType.MARKET)
    fill = ex.execute(order)
    assert fill is not None
    pf.apply_fill(fill)

    # bought 10 @ 100 = 1000 + fee 1 -> cash ~ 8999
    assert abs(pf.cash - (10_000 - 1000 - 1)) < 1e-6
    assert pf.positions["BTC/USDT"].amount == 10


def test_realized_pnl_on_close():
    pf = Portfolio(cash=10_000.0)
    ex = PaperExecutor(taker_fee=0.0, slippage=0.0)
    ex.update_mark("ETH/USDT", 100.0)

    pf.apply_fill(ex.execute(Order(symbol="ETH/USDT", side=Side.BUY, amount=5)))
    ex.update_mark("ETH/USDT", 120.0)
    pf.apply_fill(ex.execute(Order(symbol="ETH/USDT", side=Side.SELL, amount=5)))

    assert "ETH/USDT" not in pf.positions
    assert abs(pf.realized_pnl - 100.0) < 1e-6  # (120-100)*5
