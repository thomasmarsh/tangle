---
context_rev: 1
priority: P2
updated: 2026-09-12T16:16:56Z
summary: Add a reconciliation and integration planner that classifies duplicate IDs, same-node divergence, and post-integration stale consumers.
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

# Result

`braintree reconcile [--base REF] [--head REF ...] [NODES]` prints a
dependency-ordered repair plan derived read-only from Git snapshots plus the
Markdown in those snapshots; it never mutates the vault. `base` defaults to
`HEAD` and `head` to a single `HEAD`, and the planner refuses to run outside a
Git work tree or on an unknown ref. Every node under the nodes directory is read
at each ref through `git ls-tree`/`git show` and parsed with the same frontmatter
and context-edge code the other verbs use.

`index.reconcile` classifies three hazards, matching the existing
`tests/worktree-parallel.sh` scenarios:

- `duplicate-identity`: two paths that share one numeric ID, whether already
  present in `base` or introduced at different paths by different heads. This is
  the shipped duplicate-numeric-ID scenario.
- `same-node-divergence`: one node name changed by two heads (a rename on one and
  an edit on the other), which must be reconciled rather than merged blind. This
  is the shipped rename-versus-edit scenario.
- `reread-dependency` then `reconcile-consumer`: a node whose `context_rev`
  changed in a head is listed for reread, followed by each base node that pins
  the old revision, using the shared `context_pin_problem`/`stale_reason`
  verdict. This is the shipped dependency-context-drift scenario.

Steps are ordered by class, then dependency distance, then node and path, so
every bumped dependency and its reread step precede the consumers that pin it.
Output is `base`, a `head[ref]` table, and a
`steps{action,depth,node,path,pinned,current,detail}` table, or the explicit
`reconcile: 0 steps` line.

Evidence: `tests/test_bt_reconcile.py` builds throwaway Git repositories for a
cross-head duplicate, a rename-versus-edit divergence, a bumped dependency whose
consumer is ordered after it, an empty plan, an unknown ref, a non-repository
work tree, and the argument errors. `tests/worktree-parallel.sh` now runs the
planner inside its duplicate-numeric-ID, rename-versus-edit, and
dependency-context-drift scenarios and asserts the classification, the named
node, and the target-before-consumer order. `tests/test_bt_foundation.py`
covers dispatch and the help entry. `braintree check nodes`, `make test`,
`make verb-benchmark`, and `make benchmark` all pass; the verb gate and its
baseline are unchanged because no gated verb output changed.
