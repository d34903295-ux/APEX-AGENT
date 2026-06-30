"""Distributed-intelligence ("more brains") layer for APEX-AGENT PRO.

A Council of single-responsibility brains collaborates on each decision: a
Router sends work to the cost-appropriate specialist, a Verifier brain refutes
before anything ships, high-risk calls go to a weighted ensemble, memory gives
context and scorecards, and fallback chains degrade gracefully to free local
brains. See docs/BRAINS.md for the architecture and contracts.
"""
from __future__ import annotations

from apex.brains.contracts import (BrainResult, BrainTask, Decision, Risk,
                                    TaskKind, Tier)
from apex.brains.council import Council, default_brains
from apex.brains.router import Router

__all__ = [
    "Council", "Router", "default_brains",
    "BrainTask", "BrainResult", "Decision", "TaskKind", "Risk", "Tier",
]
