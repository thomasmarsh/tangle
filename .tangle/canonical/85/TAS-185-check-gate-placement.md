---
status: resolved
context_rev: 2
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Make tangle check flag a Gated on line outside # Context.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Hekate `FBK-031` finding 8 at `0.6.0+g169bad5`. `SKILL.md` says a gate is a
`Gated on [[...]].` line "in `# Context`", and the round-eight refresh scout had
to hand-roll grep checks for that structure. Probe: a scratch node with a `Gated
on` line in its `# Outcome` passes `tangle check` with zero findings, because
`src/tangle/graph_check.py` scans only the pinned context relations (`Depends
on`, `Implements`, `Requires`, `Governed by`); `Gated on` is used only to build a
diagnostic hint. The `next` form rules are already enforced by
`next-action-wikilink` and `next-not-direct-child`.

# Outcome

`tangle check` reports `gate-outside-context` for an authored
`Gated on [[TARGET]].` relation line outside a node's `# Context` section, while
the same exact relation inside `# Context` remains valid. Prose that merely
mentions or quotes the gate syntax is not a relation and remains clean.

# Done when

- `src/tangle/graph_check.py` adds the stable `gate-outside-context` finding
  code and the checker's finding-code surface documents it.
- `tests/` covers an exact gate relation outside `# Context`, a compliant gate
  inside `# Context`, and prose or quoted syntax that stays clean.
- `make test` passes.

# Result

Resolved.

- `src/tangle/graph_check.py` adds the stable `gate-outside-context` code to
  `FINDING_CODES` and the module docstring's context-edge code list, the
  anchored `GATED_LINE` relation and `_CONTEXT_BLOCK` section patterns, and
  `_check_gate_placement`, which scans the masked node text and flags each
  exact `Gated on [[X]].` line whose offset falls outside every `# Context`
  span. `_validate` calls it beside `_check_context_edges`. Anchoring both ends
  keeps prose, trailing text, and missing final periods out of the relation
  set, and masking keeps inline-code spans and fenced blocks clean.
- `tests/test_graph_check.py` adds `test_gate_outside_context_is_flagged`,
  `test_gate_inside_context_is_valid`,
  `test_quoted_gate_syntax_outside_context_stays_clean`,
  `test_prose_mentioning_the_gate_stays_clean`, and the
  `_mut_gate_outside_context` entry in the `_MUTATIONS` registry that
  `test_documented_codes_cover_every_error_class` requires. The existing
  `test_gated_dependency_on_unresolved_predecessor_passes` now places its gate
  in a `# Context` section, since a node without one offers no valid placement.
- `uv run pytest tests/test_graph_check.py -q`: 105 passed.
- `uv run tangle check`: passed (222 nodes), so the live vault has no gate
  outside `# Context` and the strict rule keeps it clean.
- `make test`: 731 passed, 3 skipped (numpy absent).
