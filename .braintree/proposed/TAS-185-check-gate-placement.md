---
context_rev: 1
priority: P2
updated: 2026-09-14T11:20:50Z
summary: Make braintree check flag a Gated on line outside # Context.
next: Add a graph-check finding for a Gated on line outside # Context and cover it with tests.
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

`braintree check` reports a finding when a `Gated on` line appears outside a
node's `# Context` section, so the documented gate placement is machine-checked.

# Done when

- `src/braintree/graph_check.py` adds a stable finding code for a `Gated on` line
  outside `# Context`, and the checker's docstring lists it.
- `tests/` covers the new finding with a positive probe and a compliant node that
  stays clean.
- The new finding code is documented on the checker's finding-code surface.
- `make test` passes.
