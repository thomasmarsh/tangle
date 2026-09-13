---
context_rev: 1
priority: P2
updated: 2026-09-13T14:03:33Z
summary: Compare retrieval policies on held-out, action-weighted engineering queries.
next: Define the held-out action-weighted retrieval comparison.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Gated on [[TAS-123-pipeline-diagnostics]].

# Outcome

Exact graph traversal, lexical search, semantic ranking, time-aware expansion, and graph propagation are compared on implicit and multi-hop queries whose gold memories change the correct action.

# Done when

- The held-out query set includes semantic disconnect, stale distractors, missing evidence, and multi-hop dependencies.
- Evidence recall and precision are reported separately from downstream action success.
- Misses are weighted by action consequence and costs include tokens, calls, and latency.
- Each candidate receives a keep, revise, or reject decision against the fixed lexical and graph baselines.
