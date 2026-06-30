"""CEX adapter via ccxt. Used only when live trading is confirmed."""
from __future__ import annotations

from apex.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.core.models import Fill, Order
from apex.execution.adapters.base import CEX_VENUES, ExchangeAdapter

log = get_logger("apex.exec.ccxt")


class CCXTAdapter(ExchangeAdapter):
    venue_type = "cex"

    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()
        self._clients: dict[str, object] = {}

    def supports(self, venue: str) -> bool:
        return (venue or "").lower() in CEX_VENUES

    def _client(self, venue: str):
        v = venue.lower()
        if v in self._clients:
            return self._clients[v]
        try:
            import ccxt
        except ImportError:
            log.warning("ccxt not installed")
            self._clients[v] = None
            return None
        creds = self.s.exchange_credentials(v)
        klass = getattr(ccxt, v, None)
        if klass is None or not creds.get("apiKey"):
            self._clients[v] = None
            return None
        self._clients[v] = klass({**creds, "enableRateLimit": True})
        return self._clients[v]

    def execute(self, order: Order) -> Fill | None:
        client = self._client(order.exchange)
        if client is None:
            log.info("no live CEX client for %s; gateway will fall back", order.exchange)
            return None
        try:  # pragma: no cover - requires live keys/network
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
            log.error("LIVE CEX order failed on %s: %s", order.exchange, exc)
            return None
