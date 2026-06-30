"""Execution algorithms for large orders: TWAP, VWAP, Iceberg.

Each algo slices a parent order into children to reduce market impact. They are
generators of child `Order`s; the gateway places the children with appropriate
delays. Keeping them pure generators makes them trivial to unit-test.
"""
from __future__ import annotations

from collections.abc import Iterator

from apex.core.models import Order


def twap(parent: Order, slices: int = 10) -> Iterator[Order]:
    """Time-Weighted Average Price: equal child sizes over time."""
    child_amt = parent.amount / slices
    for i in range(slices):
        d = parent.to_dict()
        d.pop("id", None)
        d["amount"] = child_amt
        d["algo"] = None
        d["meta"] = {**parent.meta, "algo": "twap", "slice": i + 1, "of": slices}
        yield Order.from_dict(d)


def vwap(parent: Order, volume_curve: list[float]) -> Iterator[Order]:
    """Volume-Weighted: child sizes follow an expected intraday volume curve."""
    total = sum(volume_curve) or 1.0
    for i, v in enumerate(volume_curve):
        d = parent.to_dict()
        d.pop("id", None)
        d["amount"] = parent.amount * (v / total)
        d["algo"] = None
        d["meta"] = {**parent.meta, "algo": "vwap", "slice": i + 1, "of": len(volume_curve)}
        yield Order.from_dict(d)


def iceberg(parent: Order, visible_pct: float = 0.1) -> Iterator[Order]:
    """Iceberg: only a small visible slice at a time until fully filled."""
    visible = max(parent.amount * visible_pct, 0.0)
    remaining = parent.amount
    i = 0
    while remaining > 1e-12 and visible > 0:
        amt = min(visible, remaining)
        d = parent.to_dict()
        d.pop("id", None)
        d["amount"] = amt
        d["algo"] = None
        d["meta"] = {**parent.meta, "algo": "iceberg", "slice": i + 1}
        yield Order.from_dict(d)
        remaining -= amt
        i += 1


ALGOS = {"twap": twap, "vwap": vwap, "iceberg": iceberg}
