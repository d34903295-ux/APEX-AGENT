"""Execution gateway: the ONLY component that talks to exchanges/chains.

Routing logic:
  * If live trading is disabled (default) -> always PaperExecutor.
  * If live + a CEX adapter exists for the venue -> ccxt order.
  * If live + a DEX venue -> on-chain adapter (web3/jupiter) — stubbed.

Smart routing picks the venue with the best effective price across the
adapters that hold the required balance. Large orders are sliced by the algo
named on the order (twap/vwap/iceberg).

This module fails CLOSED: any uncertainty falls back to paper so the agent can
never accidentally fire a live order it didn't fully understand.
"""
from __future__ import annotations

from apex.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.core.models import Fill, Order
from apex.execution.algos import ALGOS
from apex.execution.paper import PaperExecutor

log = get_logger("apex.exec.gateway")


class ExecutionGateway:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()
        self.paper = PaperExecutor()
        self._ccxt: dict[str, object] = {}  # exchange -> ccxt client (lazy)

    def update_mark(self, symbol: str, price: float) -> None:
        self.paper.update_mark(symbol, price)

    # ---- CEX adapter (lazy) --------------------------------------------
    def _ccxt_client(self, exchange: str):
        if exchange in self._ccxt:
            return self._ccxt[exchange]
        try:
            import ccxt  # lazy import
        except ImportError:
            log.warning("ccxt not installed; %s falls back to paper", exchange)
            self._ccxt[exchange] = None
            return None
        creds = self.s.exchange_credentials(exchange)
        if not creds.get("apiKey"):
            self._ccxt[exchange] = None
            return None
        klass = getattr(ccxt, exchange, None)
        if klass is None:
            self._ccxt[exchange] = None
            return None
        client = klass({**creds, "enableRateLimit": True})
        self._ccxt[exchange] = client
        return client

    # ---- execution ------------------------------------------------------
    def execute(self, order: Order) -> list[Fill]:
        children = self._slice(order)
        fills: list[Fill] = []
        for child in children:
            fill = self._execute_one(child)
            if fill:
                fills.append(fill)
        return fills

    def _slice(self, order: Order) -> list[Order]:
        if order.algo and order.algo in ALGOS:
            algo = ALGOS[order.algo]
            try:
                if order.algo == "vwap":
                    curve = order.meta.get("volume_curve", [1] * 10)
                    return list(algo(order, curve))
                return list(algo(order))
            except Exception as exc:  # pragma: no cover
                log.warning("algo %s failed (%s); sending parent", order.algo, exc)
        return [order]

    def _execute_one(self, order: Order) -> Fill | None:
        # FAIL CLOSED: anything other than confirmed-live CEX goes to paper.
        if not self.s.is_live or order.exchange in ("paper", ""):
            return self.paper.execute(order)

        client = self._ccxt_client(order.exchange)
        if client is None:
            log.info("no live adapter for %s; paper fill", order.exchange)
            return self.paper.execute(order)

        try:  # pragma: no cover - requires live keys
            resp = client.create_order(
                order.symbol, order.type.value, order.side.value,
                order.amount, order.price,
            )
            avg = float(resp.get("average") or resp.get("price") or order.price or 0)
            fee = float((resp.get("fee") or {}).get("cost") or 0)
            return Fill(order_id=order.id, symbol=order.symbol, side=order.side,
                        amount=order.amount, price=avg, fee=fee,
                        exchange=order.exchange, strategy=order.strategy)
        except Exception as exc:  # pragma: no cover
            log.error("LIVE order failed on %s: %s; NOT retrying as paper", order.exchange, exc)
            return None
