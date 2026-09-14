---
context_rev: 2
priority: P1
updated: 2026-09-14T19:35:47Z
summary: Deliver worktree rebase reconciliation and acceptance.
next: "[[TAS-199-normalize-worktree-change-bundles]]"
---

Parent [[TAS-192-deliver-opt-in-parallel-graph-mutation-and]].

# Context

Gated on [[TAS-193-same-directory-graph-contribution-intake]].

This is the second high-priority phase. It extends the normalized proposal model, stable lowercase identities, clone-stable project UID, and full-census index to independently committed worktree changes and treats a worktree snapshot as a declared base, never current truth. Rebase is a transport step; semantic acceptance still comes from explicit preconditions, reconciliation, candidate validation, and serialized integration.

# Outcome

An integrator can ingest worktree commits, discover what changed since their base, reconcile graph and repository effects against the current target, and accept only a fully validated combined tree.

# Done when

- Git refs and commits normalize into the same logical operations as local proposals while retaining exact repository payload and base witnesses.
- Legacy movable uppercase nodes and new stationary lowercase nodes normalize into one operation model without treating a status path move, case-only migration, or generated-view churn as an unexplained canonical deletion.
- A read-only rebase reconciliation plan classifies disjoint, replayable, stale, overlapping, deletion, identity, frontier, dependency, and unknown cases against the current target.
- Selected graph operations and repository payloads are validated together in a scratch tree before canonical acceptance.
- Acceptance uses an expected-head compare-and-swap boundary or an equivalently specified Git primitive, and retries cannot duplicate canonical IDs, dispositions, or receipts.
- Existing `braintree reconcile --base/--head` behavior remains a compatible bounded view or has a documented migration path.
- Worktree fixtures cover target movement, rename-versus-edit, concurrent creation, parent-next contention, dependency drift, exact duplicates, producer disappearance, and repository test failure.
- Detailed worktree guidance remains conditional and all direct children are resolved or deliberately disposed.
