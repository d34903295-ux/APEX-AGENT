"""Execution gateway: the ONLY component that talks to exchanges/chains.

Routing (via the adapter layer in `apex/execution/adapters/`):
  * live disabled (default)            -> PaperExecutor
  * live + venue classified CEX        -> CCXTAdapter
  * live + venue classified EVM DEX    -> EvmDexAdapter (scaffold)
  * live + venue classified Solana DEX -> SolanaDexAdapter (scaffold)

Smart routing: when an order doesn't pin a venue, `best_venue()` can pick the
cheapest venue from the latest marks per exchange. Large orders are sliced by
the algo named on the order (twap/vwap/iceberg).

Fails CLOSED: any uncertainty falls back to paper (non-live) or drops the
order with a log line (live) — it never silently invents a live fill.
"""
from __future__ import annotations

from apex.config import Settings, get_settings
from apex.core.logging import get_logger
from apex.core.models import Fill, Order
from apex.execution.adapters.base import classify_venue
from apex.execution.adapters.ccxt_adapter import CCXTAdapter
from apex.execution.adapters.evm_dex import EvmDexAdapter
from apex.execution.adapters.solana_dex import SolanaDexAdapter
from apex.execution.algos import ALGOS
from apex.execution.circuit import VenueFailover
from apex.execution.paper import PaperExecutor

log = get_logger("apex.exec.gateway")


class ExecutionGateway:
    def __init__(self, settings: Settings | None = None):
        self.s = settings or get_settings()
        self.paper = PaperExecutor()
        self.adapters = {
            "cex": CCXTAdapter(self.s),
            "evm_dex": EvmDexAdapter(self.s),
            "solana_dex": SolanaDexAdapter(self.s),
        }
        # latest price per (exchange -> symbol -> price) for smart routing.
        self._venue_marks: dict[str, dict[str, float]] = {}
        self.failover = VenueFailover()

    def update_mark(self, symbol: str, price: float, exchange: str = "paper") -> None:
        self.paper.update_mark(symbol, price)
        self._venue_marks.setdefault(exchange, {})[symbol] = price

    def best_venue(self, symbol: str, side: str) -> str | None:
        """Cheapest buy / richest sell across venues we have marks for."""
        candidates = {ex: m[symbol] for ex, m in self._venue_marks.items()
                      if symbol in m and ex != "paper"}
        if not candidates:
            return None
        return (min if side == "buy" else max)(candidates, key=candidates.get)

    # ---- execution ------------------------------------------------------
    def execute(self, order: Order) -> list[Fill]:
        fills: list[Fill] = []
        for child in self._slice(order):
            fill = self._execute_one(child)
            if fill:
                fills.append(fill)
        return fills

    def _slice(self, order: Order) -> list[Order]:
        if order.algo and order.algo in ALGOS:
            algo = ALGOS[order.algo]
            try:
                if order.algo == "vwap":
                    return list(algo(order, order.meta.get("volume_curve", [1] * 10)))
                return list(algo(order))
            except Exception as exc:  # pragma: no cover
                log.warning("algo %s failed (%s); sending parent", order.algo, exc)
        return [order]

    def _alternates(self, symbol: str, primary: str) -> list[str]:
        """Other CEX venues we have live marks for, ordered by venue name."""
        same_type = classify_venue(primary)
        return sorted(
            ex for ex in self._venue_marks
            if ex not in ("paper", primary) and classify_venue(ex) == same_type
        )

    def _execute_one(self, order: Order) -> Fill | None:
        # Non-live, or unspecified venue -> paper (the safe path).
        if not self.s.is_live or order.exchange in ("paper", ""):
            return self.paper.execute(order)

        venue_type = classify_venue(order.exchange)
        adapter = self.adapters.get(venue_type)
        if adapter is None:
            log.info("no adapter for venue %s (%s); paper fill", order.exchange, venue_type)
            return self.paper.execute(order)

        # Multi-exchange failover: try the primary, then any healthy alternate
        # that lists the same pair, migrating on venue outage. Circuit breakers
        # skip venues that are currently failing.
        candidates = self.failover.candidates(order.exchange, self._alternates(order.symbol, order.exchange))
        for venue in candidates:
            child = order if venue == order.exchange else Order.from_dict({**order.to_dict(), "exchange": venue})
            try:
                fill = self.adapters[classify_venue(venue)].execute(child)
            except Exception as exc:  # pragma: no cover - adapter raised
                log.warning("venue %s raised (%s); failing over", venue, exc)
                self.failover.record_failure(venue)
                continue
            if fill is not None:
                self.failover.record_success(venue)
                if venue != order.exchange:
                    log.warning("order %s migrated %s -> %s (failover)", order.id, order.exchange, venue)
                return fill
            self.failover.record_failure(venue)

        # All venues exhausted. For LIVE we DROP (never fake a fill); log loudly.
        log.error("all venues failed for order %s (%s); dropping (fail-closed)",
                  order.id, candidates)
        return None
