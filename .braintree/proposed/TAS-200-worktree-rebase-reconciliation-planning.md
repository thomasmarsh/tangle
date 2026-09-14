---
context_rev: 2
priority: P1
updated: 2026-09-14T19:35:47Z
summary: Build read-only worktree rebase reconciliation planning.
next: Reconcile normalized worktree proposals against a moved target.
---

Parent [[TAS-194-worktree-rebase-reconciliation-and-acceptance]].

# Context

Gated on [[TAS-199-normalize-worktree-change-bundles]].

A Git rebase can replay bytes but cannot decide graph meaning. This planner first hashes the complete target canonical store, treats that reconciled result as the proposed integration snapshot, and reports whether each worktree contribution still commutes, cleanly replays under the contract, or needs revision or an explicit semantic decision.

# Outcome

Before any branch or target ref changes, an integrator can inspect a deterministic plan for combining selected worktree contributions with the current target.

# Done when

- The planner compares each retained base, worktree head, and expected target; rebuilds overlap components across all selected contributions; and recomputes dependencies and graph predicates against their hypothetical union.
- Clean rebase is reported only when changed preconditions are proven outside the derived structural footprint, an explicit decision confirms no declared semantic read changed, replay is stable, and the complete checked result is identical. Textual patch success alone is insufficient.
- Selected graph operations and bound repository payloads apply in a scratch worktree or temporary Git tree. Symbolic lowercase IDs and timestamps remain noncanonical during planning; generated view pages derive from the candidate but do not participate as proposed source changes.
- The complete candidate runs `braintree check` and the tests required by its full repository write-set closure; a failure is attached to the responsible component and never modifies a source worktree or target ref.
- Classification covers disjoint contributions, same-node divergence, duplicate identity, parent-next contention, dependency revision drift, target-side restructuring, exact duplicate results, source conflicts, and unknown semantic interaction.
- Stable plan hashing binds the selected proposals, decisions, expected target, symbolic mapping, and required gates. Permuting proposal arrival or topologically equivalent replay order cannot change a commuting plan.
- Output tells an integrator whether to rebase, revise, decide, absorb, or proceed, and identifies the exact failed precondition and evidence needed for the next action.
- Worktree tests falsify unsafe clean-rebase claims with a patch that applies and passes structural checks while a declared semantic read changed.
