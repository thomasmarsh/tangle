---
context_rev: 1
priority: P1
updated: 2026-09-13T14:03:33Z
summary: Audit whether repository-only and oracle conditions separate on a bounded pilot.
next: Run a bounded separability pilot after recording any required live-run authorization.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Gated on [[TAS-135-corpus-validator-splits]].

# Outcome

A bounded pilot verifies that memory-required cases cannot be solved reliably from current repository state while oracle evidence makes the intended action attainable, before the full five-arm experiment spends significant tokens.

# Done when

- A preregistered 8–12-case development subset spans all four scenario families.
- Any paid or live model execution is separately authorized and records model, reasoning effort, tool version, prompt, fixture digest, and session telemetry.
- Repository-only and oracle results are paired and graded; memory-irrelevant controls remain solvable without oracle evidence.
- Cases that fail to separate are repaired or removed with reasons, without inspecting held-out outcomes.
- The phase-one corpus and contract receive a proceed, revise, or stop decision.
