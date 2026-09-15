---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Define the worker-side completion path and checker distinction for a resolved child whose parent next has not advanced.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Hekate `FBK-017` and `FBK-023` finding 3 at `0.6.0+g3bacaf5`. Round six
[[TAS-115-parent-next-advance-ownership]] already made `tangle check` report a
stale route as `next-resolved-node` and stated that the coordinator owns the
advance when the worker's write set excludes the parent. The unhandled residual
is that the worker is left between a red gate and an out-of-write-set edit with
no stated completion rule, the failure appears the moment the file moves (before
any commit), and the checker cannot distinguish the normal multi-writer handoff
transient from a genuine stale route. Hekate `FBK-023` finding 3 adds that the
parent-next advance should fold into the resolving worker's commit whenever the
write set names the parent, to remove a coordinator round trip.

# Outcome

The contract states what a frontier-child worker commits and hands off while the
parent's `next` still names the resolved child and how the coordinator restores
the plain gate, folding the parent advance into the resolving worker's commit
when its write set names the parent; the checker separates that transient handoff
state from a genuine stale route.

# Done when

- `SKILL.md` or `references/coordination.md` states the worker-side completion
  and handoff for this case.
- The checker's `next-resolved-node` diagnostic or a documented transient rule
  distinguishes the multi-writer transient from a genuine stale route.
- Folding the parent advance into the resolving worker's commit when the write
  set names the parent is stated and tested.
- Tests cover the transient and the genuine stale route.
- `tangle check` and `make test` pass.

# Result

`SKILL.md`'s parent-next mutation rule and `references/coordination.md`'s worker
handoff section now state what a frontier-child worker commits and hands off.
When the write set names the parent — or its `next` line — the advance folds into
the child's resolution commit, so no committed state routes the parent to a
resolved child and the coordinator pays no round trip for the advance (Hekate
`FBK-023` finding 3). When the write set excludes the parent, the child's
resolution commit is the worker's completion: it names the parent and the
resolved child, records the pending advance as its handoff action, never edits
outside its set, and verifies the slice with
`tangle check --allow-pending-advance PARENT`.

The checker distinguishes the two states by declaration, because it cannot
distinguish them by inference. The multi-writer transient (the parent's `next`
names an already-resolved child while the advance is still owed) and a genuine
stale route are the same Markdown, and the checker is deliberately stateless and
file-only, so `src/tangle/graph_check.py` gains
`--allow-pending-advance NODE`: it sanctions exactly the one named parent whose
`next` names an already-resolved child and relaxes nothing else, while every
unsanctioned instance stays the `next-resolved-node` failure. The sanction never
clears the advance — the coordinator's integration gate is the plain
`tangle check` — so a route that is stale rather than pending still fails
integration. `references/coordination.md` states that transient rule and the
completion path, and `src/tangle/help.py` publishes the option on
`tangle check`.

The premise held as recorded: the checker reported `next-resolved-node` for both
states, and the failure appeared with no commit. Probe in `/tmp/tangle-139`, a
4-node vault whose `TAS-001-parent` routes to a resolved `TAS-002-child`: plain
`tangle check --format toon` exited `1` with
`"next-resolved-node",".../TAS-001-parent.md"`; the same vault with
`--allow-pending-advance TAS-001-parent` exited `0` (`findings: 0`); naming a
different node (`--allow-pending-advance TAS-002-child`) exited `1` with the same
finding; and after the coordinator advanced the parent's `next` to an unfinished
`TAS-003-next`, the plain gate printed `graph check: passed (4 nodes)`. So the
transient is a declared, named, per-node state, and the plain gate remains the
integration signal.

Tests: `tests/test_graph_check.py` adds
`test_pending_advance_sanction_covers_the_multi_writer_transient`,
`test_pending_advance_sanction_accepts_the_bare_parent_id`,
`test_pending_advance_sanction_is_scoped_to_the_named_parent`,
`test_pending_advance_sanction_relaxes_nothing_else` (the sanctioned run still
fails on `context-rev-mismatch`), and
`test_help_names_the_pending_advance_sanction`, and keeps the existing
`next-resolved-node` mutation for the genuine stale route.
`tests/test_skill.py` pins the completion path in `_PARENT_NEXT_OWNERSHIP_RULE`,
the transient and declaration rule in `_PENDING_ADVANCE_RULE` and
`_PENDING_ADVANCE_REFERENCE_RULE`, and the coordination topic rule; the
falsification probe `_PENDING_ADVANCE_PROBE_STALE_ROUTE_PARAGRAPH` feeds the
pre-change paragraph — which already defined the stale route and the ownership
exception but stated no completion path and no transient distinction — through
the same `_assert_contains` guard in
`test_pending_advance_guard_rejects_the_pre_change_stale_route_paragraph`, so the
test fails when the guard stops detecting the rule rather than passing vacuously.

Evidence: `uv run pytest -q tests/test_graph_check.py` -> 97 passed;
`uv run pytest -q tests/test_skill.py` -> 75 passed; `uv run ruff check` -> all
checks passed; `uv run mypy` -> no issues in 72 source files;
`tangle check` -> `graph check: passed (196 nodes)`; `make test` -> 664
passed, 3 skipped, 79 deselected. `SKILL.md` grew 13,624 -> 14,151 bytes, inside
the 16,000-byte `test_core_stays_concise` bound. No node pins this node and it
pins no context-bearing dependency, so `context_rev` stays `1` and no consumer
reconciliation was needed. Parent [[TAS-137-usage-feedback-hardening-round-seven]]
named this node in the write set, so this change advanced its `next` to
[[TAS-140-allocation-lifecycle-visibility]] with the parent's `updated`
refreshed and its `context_rev` unchanged.
