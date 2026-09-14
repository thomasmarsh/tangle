---
context_rev: 1
priority: P2
updated: 2026-09-14T11:20:50Z
summary: Require the brief to name the resolved-sibling compiler seams the change can force.
next: Name the resolved-sibling compiler seams in the brief and classify a mechanical compiler-forced edit as in-scope in references/coordination.md.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Tangle `FBK-031` finding 1 at `0.6.0+g169bad5`, recorded after round eight
[[TAS-158-write-set-closure-generators-and-manifests]] added "exhaustive matches
and struct literals on the changed types" to the compile-and-golden closure. Four
of eleven leaves still needed a resolved sibling's file to stay green or to make
the behavior real: a new `TacticKind` made another leaf's `compiled_tactic` match
non-exhaustive, a tightened contract invalidated a sibling fixture and needed a
shared `required_profile_params` seam, a test could not construct
`CompiledFacility`, and `compiled_profile` dropped fields `validate_v2` required.
Three workers stopped and asked instead of editing.

# Outcome

`references/coordination.md` requires the coordinator to name, in the brief, every
resolved-sibling file the approved change can force — exhaustive matches, struct
literals, generated schema, goldens, and lockfile — alongside the "gates my
artifact enters" line, and states that a mechanical compiler-forced edit to a
resolved sibling's file is in the assigned closure and does not require
escalation.

# Done when

- `references/coordination.md` carries the resolved-sibling brief rule and the
  compiler-forced in-scope classification.
- A contract test in `tests/test_skill.py` pins the rule.
- `make test` passes.
