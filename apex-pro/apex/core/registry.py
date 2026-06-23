"""Plugin registry — the heart of the hot-swappable strategy system.

Strategies (and other plugins) register themselves with a decorator. The
strategy-engine can then enable/disable them at runtime ("in caliente").
"""
from __future__ import annotations

from typing import Callable, Generic, TypeVar

T = TypeVar("T")


class Registry(Generic[T]):
    def __init__(self, kind: str) -> None:
        self.kind = kind
        self._factories: dict[str, Callable[..., T]] = {}

    def register(self, name: str) -> Callable[[Callable[..., T]], Callable[..., T]]:
        def deco(factory: Callable[..., T]) -> Callable[..., T]:
            key = name.lower()
            if key in self._factories:
                raise ValueError(f"{self.kind} '{name}' already registered")
            self._factories[key] = factory
            return factory

        return deco

    def create(self, name: str, *args, **kwargs) -> T:
        key = name.lower()
        if key not in self._factories:
            raise KeyError(f"unknown {self.kind}: {name!r} (available: {self.available()})")
        return self._factories[key](*args, **kwargs)

    def available(self) -> list[str]:
        return sorted(self._factories)


# Global strategy registry. Importing apex.strategies populates it.
STRATEGY_REGISTRY: Registry = Registry("strategy")
