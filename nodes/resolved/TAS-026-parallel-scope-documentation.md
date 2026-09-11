---
context_rev: 1
priority: P1
updated: 2026-09-11T11:36:00Z
summary: Documentation now bounds parallel support to coordinated, disjoint worktree assignments.
---

# Context

Parent [[TAS-021-parallel-agent-hardening]].

# Outcome

`README.md` and `BENCHMARK.md` claim only that the graph is merge-friendly for disjoint, coordinator-assigned nodes unless broader behavior is proven, and they cite reproducible evidence and remaining coordination limits.

# Done when

Documentation scope matches the implemented ownership and integration guarantees, the benchmark reports the real-worktree scenarios and commands, and no autonomous-locking or globally current worktree claim remains.

# Result

`README.md` and `BENCHMARK.md` document the six `sh tests/worktree-parallel.sh` scenarios, coordinator-only integration/resolution, advisory claims, snapshot limits, ID allocation, and serialized shared paths. The screen and full test suite passed on 2026-09-11.
