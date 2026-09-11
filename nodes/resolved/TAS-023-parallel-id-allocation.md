---
context_rev: 1
priority: P1
updated: 2026-09-11T11:29:37Z
summary: Defined collision-safe numeric node allocation for parallel agents.
---

# Context

Parent [[TAS-021-parallel-agent-hardening]].

# Outcome

Parallel workers receive coordinator-preallocated IDs or disjoint numeric ranges, while the skill states that a local filename search is not a reservation, autonomous allocation requires an atomically shared reservation mechanism, and branch-local owner metadata cannot prevent cross-worktree races.

# Done when

The documented protocol and focused assertions distinguish collision checking from reservation and exclude branch-local metadata as an autonomous allocation safeguard.

# Result

`SKILL.md` now requires coordinator-preallocated IDs or explicitly disjoint numeric ranges for parallel workers; `find` is collision detection only, while autonomous allocation requires an atomically shared reservation visible across worktrees. `tests/skill.sh` asserts each boundary.
