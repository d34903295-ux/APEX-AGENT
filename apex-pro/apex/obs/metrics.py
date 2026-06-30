"""Minimal, dependency-free Prometheus-compatible metrics.

Produces valid Prometheus text-exposition output so any Prometheus/Grafana can
scrape `/metrics` — without pulling in prometheus_client. Supports counters and
gauges with a single optional label set. Thread-unsafe by design (drive from
one asyncio loop, like the rest of APEX).
"""
from __future__ import annotations

from typing import Iterable


def _fmt_labels(labels: dict[str, str]) -> str:
    if not labels:
        return ""
    inner = ",".join(f'{k}="{str(v)}"' for k, v in sorted(labels.items()))
    return "{" + inner + "}"


class _Metric:
    kind = "untyped"

    def __init__(self, name: str, help: str = "") -> None:
        self.name = name
        self.help = help
        self.samples: dict[tuple, float] = {}

    def _key(self, labels: dict[str, str] | None) -> tuple:
        return tuple(sorted((labels or {}).items()))

    def render(self) -> list[str]:
        out = [f"# HELP {self.name} {self.help}", f"# TYPE {self.name} {self.kind}"]
        if not self.samples:
            out.append(f"{self.name} 0")
        for key, val in self.samples.items():
            out.append(f"{self.name}{_fmt_labels(dict(key))} {val}")
        return out


class Counter(_Metric):
    kind = "counter"

    def inc(self, amount: float = 1.0, **labels) -> None:
        k = self._key(labels)
        self.samples[k] = self.samples.get(k, 0.0) + amount


class Gauge(_Metric):
    kind = "gauge"

    def set(self, value: float, **labels) -> None:
        self.samples[self._key(labels)] = float(value)

    def inc(self, amount: float = 1.0, **labels) -> None:
        k = self._key(labels)
        self.samples[k] = self.samples.get(k, 0.0) + amount


class Registry:
    def __init__(self) -> None:
        self._metrics: dict[str, _Metric] = {}

    def counter(self, name: str, help: str = "") -> Counter:
        m = self._metrics.get(name)
        if m is None:
            m = self._metrics[name] = Counter(name, help)
        return m  # type: ignore[return-value]

    def gauge(self, name: str, help: str = "") -> Gauge:
        m = self._metrics.get(name)
        if m is None:
            m = self._metrics[name] = Gauge(name, help)
        return m  # type: ignore[return-value]

    def render(self) -> str:
        lines: list[str] = []
        for m in self._metrics.values():
            lines.extend(m.render())
        return "\n".join(lines) + "\n"

    def names(self) -> Iterable[str]:
        return self._metrics.keys()


# Process-wide registry.
REGISTRY = Registry()

# Pre-declared metrics (so /metrics is populated even before first event).
TICKS = REGISTRY.counter("apex_ticks_total", "Market ticks ingested")
SIGNALS = REGISTRY.counter("apex_signals_total", "Signals emitted by strategies")
ORDERS = REGISTRY.counter("apex_orders_total", "Risk-approved orders")
FILLS = REGISTRY.counter("apex_fills_total", "Executed fills")
REJECTIONS = REGISTRY.counter("apex_rejections_total", "Signals rejected by risk")
PAUSES = REGISTRY.counter("apex_pauses_total", "Risk auto-pauses")
EQUITY = REGISTRY.gauge("apex_equity", "Portfolio equity (base currency)")
CASH = REGISTRY.gauge("apex_cash", "Portfolio cash (base currency)")
DRAWDOWN = REGISTRY.gauge("apex_drawdown_ratio", "Current drawdown 0..1")
OPEN_POSITIONS = REGISTRY.gauge("apex_open_positions", "Open positions count")
PAUSED = REGISTRY.gauge("apex_paused", "1 if the agent is paused, else 0")

# --- distributed-intelligence ("more brains") layer -------------------------
BRAIN_TASKS = REGISTRY.counter("apex_brain_tasks_total", "Brain tasks handled")
BRAIN_FALLBACKS = REGISTRY.counter("apex_brain_fallbacks_total", "Brain fallback escalations/degradations")
BRAIN_VERIFICATIONS = REGISTRY.counter("apex_brain_verifications_total", "Verifier outcomes")
BRAIN_DECISIONS = REGISTRY.counter("apex_brain_decisions_total", "Council decisions by action")
BRAIN_COST_USD = REGISTRY.gauge("apex_brain_cost_usd_total", "Cumulative LLM spend (USD est.)")
BRAIN_CONSENSUS = REGISTRY.gauge("apex_brain_consensus_ratio", "Last ensemble consensus ratio 0..1")
