---
status: proposed
context_rev: 3
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Document and verify the opt-in worktree rebase workflow.
next: Exercise and document worktree reconciliation from submission through recovery.
---

Parent [[TAS-194-worktree-rebase-reconciliation-and-acceptance]].

# Context

Gated on [[TAS-201-worktree-cas-acceptance-and-recovery]].

This task closes the second release without pushing worktree complexity into the default skill path. The existing coordination reference may route to a narrower change-intake or integration reference when the worktree uses proposal reconciliation.

# Outcome

A fresh integrator can reconcile and accept selected worktree contributions against a moving target using installed conditional documentation, while ordinary direct and assigned-worktree workflows remain concise.

# Done when

- Conditional documentation distinguishes ordinary Git rebase, existing exclusive-write-set integration, and proposal-based reconciliation; it states exactly when each path is sufficient and when semantic review is mandatory.
- Command help covers base/head/target selection, plan and decision files, scratch validation, expected-head apply, exit codes, recovery, unsupported Git shapes, and the fact that leases confer no authorization.
- `tests/worktree-parallel.sh` or a focused successor demonstrates concurrent creation, rename-versus-edit, dependency drift, parent contention, exact duplicate outcomes, moved target, producer disappearance, failed repository gates, CAS loss, and recovery after the accepted commit but before receipt publication.
- Compatibility tests pin the existing bounded `tangle reconcile --base/--head` view and verify any new richer output only behind explicit options or new verbs.
- A control path proves disjoint, preassigned worktrees may continue using the current claim, handoff, and serial-integration contract without creating change bundles.
- Installation and reference tests prove progressive disclosure: `SKILL.md` contains only the escalation route, the detailed workflow is loaded conditionally, and per-command help carries syntax.
- Worktree guidance makes the project-owned hash census and Markdown projections implicit command behavior, not handoff duties. It distinguishes full 128-bit lowercase Crockford Base32 project and node identity, local alias, collision-aware terminal abbreviation, content hash, and Git object identity without requiring clients to maintain mappings or view files; durable and machine-readable evidence always retains full IDs.
- `tangle check`, `make test`, and `make test-benchmarks` pass because this phase touches the worktree harness or its committed baseline.
