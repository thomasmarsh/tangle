---
context_rev: 2
priority: P1
updated: 2026-09-14T19:35:47Z
summary: Normalize Git worktree contributions into change bundles.
next: Implement the Git-ref adapter and repository payload binding.
---

Parent [[TAS-194-worktree-rebase-reconciliation-and-acceptance]].

# Context

Gated on [[TAS-193-same-directory-graph-contribution-intake]].

This task begins only after local intake proves the v1 operation model. It extends transport, not canonical graph semantics, and reuses the current Git snapshot reader and full-census canonical parser behind `braintree reconcile`.

# Outcome

A committed worktree contribution can be represented as a verified v1 proposal whose graph operations and exact non-graph repository effect share one retained base and one content-addressed identity.

# Done when

- A read-only adapter accepts explicit base and head refs, retains or verifies the base witness, and emits the same normalized graph operations, preconditions, footprints, and proposal digest used by local submission.
- The repository payload is an exact Git tree or commit reference, or a content-addressed patch with base and result tree OIDs; graph operations cannot claim a task transition whose required implementation remains only on an unbound branch.
- Legacy identity-preserving status moves and case/path migrations are distinguished from deletion; new stationary nodes express status as content. An unexplained canonical-node deletion is `unknown` or a policy error until translated into explicit retirement, and generated-view changes are excluded from graph operations. Raw source deletion never becomes a graph disposition.
- New worktree nodes retain proposal-local symbols until acceptance. A lowercase collision-resistant ID authored speculatively on a branch grants no canonical identity, and a legacy numeric ID remains subject to remapping or collision classification.
- Renames, mode changes, binary files, symlinks, submodules, missing objects, shallow history, dirty worktrees, and a ref moving during collection have explicit supported or rejected behavior.
- Existing `reconcile --base/--head` output remains compatible while sharing the new adapter internally or through a compatibility projection.
- Tests use throwaway repositories and real worktrees to cover graph-only, repository-only, compound, legacy move, stationary status edit, case/path migration, view-only churn, deletion, missing-base, mismatched project UID, and moved-ref inputs without mutating the target branch.
