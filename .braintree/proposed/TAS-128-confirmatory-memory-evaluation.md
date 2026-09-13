---
context_rev: 1
priority: P1
updated: 2026-09-13T20:12:41Z
summary: Run the frozen confirmatory evaluation and settle the supported memory contract.
next: Freeze the selected mechanisms and confirmatory protocol.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-127-uncertainty-provenance-security]] at context_rev 1.

# Outcome

A held-out confirmatory run determines which claims and mechanisms belong in the Braintree contract and documents the remaining limits.

# Done when

- Selected mechanisms, prompts, models, budgets, graders, and analysis are frozen before held-out execution.
- Paired results include uncertainty intervals, missing samples, and correctness-cost Pareto comparisons.
- The report distinguishes confirmed, rejected, exploratory, and untested claims.
- Accepted contract changes, benchmark baselines, documentation, and reversal criteria are committed and all required suites pass.
