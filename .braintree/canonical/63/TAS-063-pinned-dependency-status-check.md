---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: graph-check reports a pinned dependency that is not resolved, and the skill states when a DEF or DEC is resolved.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R5 from Hekate `THO-006-braintree-friction-shared-render-layer` F1:
the loop says to confirm a pinned dependency is resolved, but
`graph-check` and `bt stale` both pass a pin whose target is still `proposed`,
and the skill never states when a `DEF`/`DEC` becomes resolved.

# Outcome

A pinned dependency that is not `resolved` is reported by the tooling, or the
skill explicitly exempts knowledge nodes and states the intended ordering; the
skill also states when a settled `DEF`/`DEC` is resolved.

# Done when

- `graph-check` or `bt stale` reports a pinned dependency whose target is `proposed` or `blocked`, or `SKILL.md` documents the exemption and ordering.
- `SKILL.md` states that a settled `DEF`/`DEC` is resolved.
- A regression test covers the reported state.
- `make test` passes.

# Result

Took the tooling branch. `graph-check` now reports a pinned `Depends on` target
whose status is `proposed`, `active`, or `blocked` as
`pinned dependency <target> is <status>, not resolved`. The check is
independent of `--allow-stale`, because that gate relaxes only the revision
equality and the pinned-target status is not a staleness question.

`SKILL.md` states the new check, that `--allow-stale` does not relax it, and
that a settled `DEF` or `DEC` is `resolved` while an unsettled one stays
`proposed`.

Evidence:

- `_check_context_edges` in `src/braintree/graph_check.py` reports a pinned
  dependency whose target status is not `resolved`.
- `test_pinned_dependency_not_resolved` and
  `test_allow_stale_still_rejects_unresolved_pin` in `tests/test_graph_check.py`
  cover the reported state and the `--allow-stale` non-exemption.
- `test_skill_canonical_edge_and_lifecycle_contract` asserts the stated
  dependency-status and `DEF`/`DEC` settlement contract.
- The live vault still passes the plain gate: `graph-check` counts 82 nodes and
  every pinned target is resolved.
- `make test` passes.
