"""Structured logging. Uses `rich` when available, plain logging otherwise."""
from __future__ import annotations

import logging
import os

_CONFIGURED = False


def setup_logging(level: str | None = None) -> None:
    global _CONFIGURED
    if _CONFIGURED:
        return
    lvl = (level or os.getenv("APEX_LOG_LEVEL", "INFO")).upper()
    try:
        from rich.logging import RichHandler

        logging.basicConfig(
            level=lvl,
            format="%(message)s",
            datefmt="[%X]",
            handlers=[RichHandler(rich_tracebacks=True, markup=True)],
        )
    except Exception:  # pragma: no cover
        logging.basicConfig(
            level=lvl,
            format="%(asctime)s | %(levelname)-7s | %(name)s | %(message)s",
        )
    _CONFIGURED = True


def get_logger(name: str) -> logging.Logger:
    setup_logging()
    return logging.getLogger(name)
