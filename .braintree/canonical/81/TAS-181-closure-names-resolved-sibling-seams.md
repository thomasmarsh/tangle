---
status: resolved
context_rev: 2
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Resolve compiler closure precedence at resolved-sibling seams.
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

# Result

Resolved `references/coordination.md`, `tests/test_skill.py`.

- `references/coordination.md`, "## Parallel worktree contract": the dispatch
  paragraph now requires the brief to name the known resolved-sibling compiler
  seams the approved change can force — the concrete paths or the resolved
  owners — before dispatch. The write-set closure bullet now states the
  precedence: a compiler- or touched-test-forced conformance edit (exhaustive
  match, constructor, fixture, or derived consumer) is in the change's closure
  even when a resolved sibling owns the path, whether named before dispatch or
  discovered only by the compiler or a touched test; the worker makes the
  mechanical edit and reports it with the closure rather than escalating.
  Behavioral, public-contract, and landed-seam meaning changes still stop and
  escalate, as does a path owned by another node or a shared hub that the
  compiler and touched tests do not mechanically force.
- `tests/test_skill.py`: added `_RESOLVED_SIBLING_CLOSURE_PRECEDENCE_RULE` with
  `test_closure_takes_precedence_at_a_resolved_sibling_seam`, and a
  falsification guard test. Superseded by
  `TAS-187-round-ten-review-reconciliation`: the synthetic
  `_RESOLVED_SIBLING_CLOSURE_PRE_CHANGE` probe was removed and the guard now
  probes with the verbatim `_WRITE_SET_CLOSURE_PRE_CHANGE`, and the escalation
  sentence was reworded so `_WRITE_SET_CLOSURE_RULE`'s tail was re-cut to match.
- Commands: `uv run pytest tests/test_skill.py -q -k "closure or
  resolved_sibling or write_set or precedence"` (5 passed) and `make test`
  (green). `braintree check` passes.
