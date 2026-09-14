---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: A dependency on a not-yet-resolved predecessor is a documented unpinned `Gated on` gate line, and the missing-pin and unresolved-target diagnostics name it.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N8: a node that knows it depends on a predecessor which is not yet resolved has
no sanctioned way to record that. An unpinned context edge fails as a missing
pin and a pinned edge fails because the target is not resolved, and neither
diagnostic names the sanctioned form. The contract says to confirm a pinned
dependency is resolved before executing, but not how to gate on one before that
point.

# Outcome

A worker can record a known dependency on an unresolved predecessor without
failing the checker, or is told the one sanctioned alternative in the failure.

# Done when

- `SKILL.md` states how to record a dependency on a predecessor that is not yet resolved, or the checker accepts a bounded not-yet-resolved form.
- The unresolved-target and missing-pin diagnostics name that sanctioned form.
- Regression tests cover the chosen behavior and `make test` passes.

# Result

Took the documentation branch: the one sanctioned representation is a gate, the
unpinned `Gated on` line in `# Context`, and both context-edge diagnostics name
it.

- The gate is deliberately not a context relation, so it needs no pin and the
  checker accepts it while the target is unresolved. `GATED_RELATION` in
  `graph_check.py` is the single spelling, and the `CONTEXT_RELATIONS` comment
  states why `Gated on` is absent from it, so `stale`, `impact`, and the context
  views keep reading only the consumable edges.
- `SKILL.md` states the form, that a gated node stays `proposed` until it can
  execute, that the gate is never pinned, the exact search that finds gates for
  reconciliation, and that the pinned `Depends on` edge replaces the gate once
  the target resolves.
- `_gate_hint` in `graph_check.py` renders the same clause for both
  diagnostics, and only while the target is `proposed`, `active`, or `blocked`;
  an unpinned edge to a resolved target keeps the plain missing-pin message
  because the gate does not apply there.

Evidence:

- `test_gated_dependency_on_unresolved_predecessor_passes` asserts a gate to a
  proposed target passes the checker,
  `test_missing_pin_to_unresolved_target_names_the_gated_form` and
  `test_pinned_dependency_not_resolved` assert both diagnostics name the gate
  form for the unresolved target, and `test_missing_context_rev_pin` asserts
  the resolved-target message does not name it.
- `test_skill_gated_dependency_contract` pins the `SKILL.md` contract text.
- `make test` and `braintree check nodes` pass.
