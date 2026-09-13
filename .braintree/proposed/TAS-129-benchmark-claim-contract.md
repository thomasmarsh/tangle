---
context_rev: 1
priority: P1
updated: 2026-09-13T14:03:33Z
summary: Specify the benchmark claim, memory boundary, causal arms, and decision criteria.
next: Write the evaluation contract without making live model calls.
---

Parent [[TAS-121-evaluation-foundation]].

# Outcome

A concise benchmark contract defines exactly what Braintree claims to improve, what information counts as currently observable, and how correctness and total interaction cost decide the result.

# Done when

- The contract defines memory-dependent downstream action quality as the primary target.
- The reconstructibility test covers unavailable, unreliable, ambiguous, nondeterministic, and disproportionately costly reacquisition.
- Repository-only, raw-history, flat-memory, Braintree, and oracle arms have fixed meanings.
- Primary endpoints, pipeline diagnostics, cost metrics, unit of analysis, statistical comparisons, and correctness-before-cost gates are specified.
- Exploratory and held-out decisions, version pins, and authorization requirements for live runs are explicit.
- Contract tests protect any literal protocol required by the harness.
