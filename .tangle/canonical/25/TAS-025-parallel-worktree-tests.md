---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Real Git worktree tests enforce six parallel-execution scenarios.
---

# Context

Parent [[TAS-021-parallel-agent-hardening]].

# Outcome

Automated real-worktree tests demonstrate disjoint-edit success and expose or guard duplicate Focus selection, duplicate numeric IDs with different slugs, status rename versus same-node edit, dependency drift during consumer work, and the parent-completion barrier before all worker evidence is integrated.

# Done when

All six scenarios create and remove disposable repositories or worktrees deterministically, assert semantic graph outcomes rather than Git exit codes alone, and pass through the standard test entry point.

# Result

2026-09-11T12:00:00Z: `tests/worktree-parallel.sh` runs all six disposable real-worktree scenarios and is invoked by `make test`.
