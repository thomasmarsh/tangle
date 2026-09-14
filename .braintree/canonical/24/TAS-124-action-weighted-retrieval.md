---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Compare retrieval policies on held-out, action-weighted engineering queries.
disposition: abandoned
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-123-pipeline-diagnostics]] at context_rev 3.

# Outcome

Exact graph traversal, lexical search, semantic ranking, time-aware expansion, and graph propagation are compared on implicit and multi-hop queries whose gold memories change the correct action.

# Done when

- The held-out query set includes semantic disconnect, stale distractors, missing evidence, and multi-hop dependencies.
- Evidence recall and precision are reported separately from downstream action success.
- Misses are weighted by action consequence and costs include tokens, calls, and latency.
- Each candidate receives a keep, revise, or reject decision against the fixed lexical and graph baselines.

# Result

Not executed; abandoned on the round-six diagnostics. The 540-sample causal
result records zero retrieval-miss labels: every memory arm delivered every
required source, because the shared memory budget (8) meets or exceeds the
largest case (5 episodes), so the development corpus is retrieval-saturated and
cannot demonstrate a retrieval-policy difference. Per the contract's mechanism
rule — keep only mechanisms that improve the correctness-cost trade-off — this
workstream is retired rather than run, and it no longer gates
[[TAS-128-confirmatory-memory-evaluation]]. A later corpus with cases larger
than the memory budget can reopen it as a new node.
