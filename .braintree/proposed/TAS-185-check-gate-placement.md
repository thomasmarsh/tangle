---
context_rev: 2
priority: P2
updated: 2026-09-14T11:29:16Z
summary: Make braintree check flag a Gated on line outside # Context.
next: Add gate-outside-context for exact relation lines and cover valid placement and prose exclusions with tests.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Tangle `FBK-031` finding 8 at `0.6.0+g169bad5`. `SKILL.md` says a gate is a
`Gated on [[...]].` line "in `# Context`", and the round-eight refresh scout had
to hand-roll grep checks for that structure. Probe: a scratch node with a `Gated
on` line in its `# Outcome` passes `braintree check` with zero findings, because
`src/braintree/graph_check.py` scans only the pinned context relations (`Depends
on`, `Implements`, `Requires`, `Governed by`); `Gated on` is used only to build a
diagnostic hint. The `next` form rules are already enforced by
`next-action-wikilink` and `next-not-direct-child`.

# Outcome

`braintree check` reports `gate-outside-context` for an authored
`Gated on [[TARGET]].` relation line outside a node's `# Context` section, while
the same exact relation inside `# Context` remains valid. Prose that merely
mentions or quotes the gate syntax is not a relation and remains clean.

# Done when

- `src/braintree/graph_check.py` adds the stable `gate-outside-context` finding
  code and the checker's finding-code surface documents it.
- `tests/` covers an exact gate relation outside `# Context`, a compliant gate
  inside `# Context`, and prose or quoted syntax that stays clean.
- `make test` passes.
