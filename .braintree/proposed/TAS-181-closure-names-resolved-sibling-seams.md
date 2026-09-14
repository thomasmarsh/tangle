---
context_rev: 2
priority: P2
updated: 2026-09-14T11:27:54Z
summary: Resolve compiler closure precedence at resolved-sibling seams.
next: Define known-seam briefing, mechanical closure authorization, and the semantic escalation boundary in references/coordination.md.
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

The existing rules conflict at exactly this boundary: the compile-and-golden
closure includes every required exhaustive match and struct literal, but the
same paragraph tells a worker to stop for a path owned by another node. A
resolved sibling's mechanically forced consumer is both. The repair must state
which rule wins without authorizing a behavioral or public-contract change to a
landed seam.

# Outcome

`references/coordination.md` requires the coordinator to name the known
resolved-sibling compiler seams and concrete paths or owners the approved change
can force before dispatch. A compiler- or touched-test-forced conformance edit
to an exhaustive match, constructor, fixture, or derived consumer is in the
change's closure even when a resolved sibling owns the path; discovering an
unnamed mechanical consumer widens and is reported with the closure rather than
triggering an owned-seam escalation. A change to behavior, public contract, or
the meaning of the landed seam still escalates.

# Done when

- `references/coordination.md` requires the brief to name known
  resolved-sibling compiler paths or owners before dispatch.
- The closure rule explicitly takes precedence for mechanically forced
  conformance edits, including a consumer discovered only by the compiler or a
  touched test.
- The rule preserves escalation for behavioral, public-contract, or landed-seam
  meaning changes.
- A contract test in `tests/test_skill.py` pins the rule.
- `make test` passes.
