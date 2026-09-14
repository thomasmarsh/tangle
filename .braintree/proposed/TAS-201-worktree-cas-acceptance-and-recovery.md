---
context_rev: 2
priority: P1
updated: 2026-09-14T19:35:47Z
summary: Implement compare-and-swap worktree acceptance and recovery.
next: Accept validated worktree candidates through an expected-head boundary.
---

Parent [[TAS-194-worktree-rebase-reconciliation-and-acceptance]].

# Context

Gated on [[TAS-200-worktree-rebase-reconciliation-planning]].

This task consumes only a fully decided, current reconciliation plan. It must use Git plumbing that does not depend on another worktree's mutable index and must not force-push or rewrite producer branches.

# Outcome

A validated worktree candidate becomes one coherent canonical repository commit exactly once, or the target remains unchanged and the contribution returns to reconciliation.

# Done when

- Apply reruns the complete target-store hash census and rereads the expected target, proposal and decision digests, retained bases, and required Git objects immediately before acceptance; any movement invalidates the plan.
- Real lowercase collision-resistant node IDs and one host-clock timestamp are materialized into the exact candidate, then graph checking and all plan-required repository tests rerun on those exact bytes rather than the illustrative dry-run tree.
- The acceptance record and graph plus repository effects inhabit one candidate tree. Commit construction avoids the shared working-tree index, and the target ref update uses compare-and-swap semantics against the expected old OID.
- A failed ref update publishes no terminal receipt, canonical mapping, index delta, or Markdown projection. The losing attempt discards its tentative authority and timestamp and replans against the winning head; a deterministic candidate ID may recur but is not canonical before CAS, and legacy same-host reservations do not allocate new-format identities.
- After success, receipts identify the integration, proposals, dispositions, canonical IDs, commit OID, relevant gates, and explicit decisions. Retry searches canonical history first and reconstructs missing receipts instead of applying again.
- Worktree cleanup is bounded and recoverable; no command resets, deletes, or rewrites a user's worktree or branch as an implicit side effect. Authorization to update a ref remains external to the integration lease.
- After CAS, the accepted checkout's next command can reconstruct the exact index and views from canonical Markdown even if projection publication or receipt delivery was interrupted.
- Race and fault-injection tests cover two integrators, moved target, duplicate tentative IDs, test failure, crash before ref update, crash after ref update, and receipt recovery. The canonical history has at most one terminal disposition per proposal.
