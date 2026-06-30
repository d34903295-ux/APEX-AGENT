# Development Methodology — Superpowers

APEX-AGENT PRO is built and maintained using **Superpowers**, the open-source
(MIT) skills/methodology library for coding agents by **Jesse Vincent (obra)** —
<https://github.com/obra/superpowers>. This document distills the parts we
apply, with attribution, so the workflow is in-repo even without the plugin.

> Install it for your agent: `scripts/install_superpowers.sh` (or
> `/plugin install superpowers@claude-plugins-official` in Claude Code).

## The loop we follow

```
brainstorm → write spec → write plan → TDD implement (red→green→refactor)
          → request code review → address review → verify → finish branch
```

### 1. Brainstorming (before any code)
Turn the idea into a short, explicit design. State assumptions, constraints and
success criteria. For APEX, the "design" for each new strategy is: *edge
hypothesis, data inputs, entry/exit rules, risk parameters, failure modes.*

### 2. Writing plans
Decompose into small, independently verifiable tasks an "enthusiastic junior
with no context" could execute. Emphasise **YAGNI** and **DRY**. Each task has a
clear done-condition and a test.

### 3. Test-Driven Development (red → green → refactor)
Write the failing test first, make it pass minimally, then refactor. APEX's
safety invariants (risk caps, auto-pause, Kelly bounds, Monte Carlo gate, the
MEV ethics-guard) are encoded as tests *first* — see `tests/`.

### 4. Subagent-driven execution
For larger work, dispatch focused subagents per task against the stable
interfaces (bus, domain models, registry), then inspect and integrate. Keeps
context tight and parallelism high.

### 5. Code review & verification
Request review of the diff; address findings; **verify by running the app**, not
just by reading code (`python -m apex.main` must produce paper fills; `pytest`
must be green). Nothing is "done" until verified.

### 6. Finishing a branch
Clean history, green tests, updated docs and ROADMAP, then open the PR.

## How this maps to APEX
- **Hot-swap strategies** ↔ writing-plans + TDD per strategy, gated by
  backtest + Monte Carlo + 24h paper before live (see `docs/TESTING.md`).
- **Safety first** ↔ invariants-as-tests; the risk-manager is the verification
  surface.
- **Living roadmap** ↔ [`ROADMAP.md`](../../ROADMAP.md), updated every change.

## Attribution
Superpowers © Jesse Vincent, MIT License. This file paraphrases its publicly
documented methodology for use within this project; the canonical, full skills
live in the upstream repository.
