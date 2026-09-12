---
context_rev: 1
priority: P2
updated: 2026-09-12T15:09:27Z
summary: Add a reconciliation and integration planner that classifies duplicate IDs, same-node divergence, and post-integration stale consumers.
next: Classify integration conflicts from a Git change set and emit the reconciliation order.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

The parallel-worktree contract assigns conflict classification and reconciliation
ordering to coordinator judgment: duplicate numeric IDs across snapshots,
same-node rename versus edit divergence, and consumers that go stale only after
a change set is integrated. A deterministic classifier over the derived graph
can surface these and order the repairs.

# Outcome

Given a base and head or a Git change set, the planner reports duplicate
identities, same-node divergence, and the consumers that become stale after
integration, ordered so each pinned dependency is reconciled after its target.

# Done when

- The classifier covers the existing worktree-parallel scenarios.
- Output is a dependency-ordered repair plan, not a raw diff.
- Tests reuse or extend `tests/worktree-parallel.sh`.
- `make test` passes.
