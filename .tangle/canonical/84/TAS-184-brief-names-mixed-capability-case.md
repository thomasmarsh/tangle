---
status: resolved
context_rev: 2
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Require a falsifying mixed-capability case for shared-stage assumptions.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Hekate `FBK-031` finding 7 at `0.6.0+g169bad5`. A leaf changed a shared stage's
maneuver resolution so every route-state agent was assumed to carry a target
clearance; a v2 scenario mixing a lateral mode with a lateral-incapable mode on
one facility panicked, and the existing tests never exercised the mix. No brief
rule requires an adversarial mixed-capability input. `rg -in
'adversarial\|mixed-capability\|shared stage\|acceptance input' SKILL.md
references/` matches nothing.

# Outcome

The increment-brief guidance requires a shared-stage change that assumes new
state or capability across heterogeneous participants to name a falsifying
mixed-capability acceptance input: one participant carries the new state or
capability and an existing participant in the same stage does not. The brief
also names the expected fallback or rejection behavior, so a non-panic alone is
not treated as acceptance.

# Done when

- The brief rule is conditional on a shared-stage change assuming participant
  state or capability, rather than applying to every shared-stage edit.
- It requires a case combining a participant with the new state or capability
  and an existing participant without it.
- It requires expected fallback or rejection behavior for that case.
- A contract test in `tests/test_skill.py` pins the rule.
- `make test` passes.

# Result

`references/authoring.md` carries the rule in "Decomposition and roll-up", as a
new paragraph after the entered-gate brief paragraph: when a shared-stage change
assumes new state or capability across heterogeneous participants, the increment
brief names a falsifying mixed-capability acceptance input — one participant
carries the new state or capability and an existing participant in the same
stage does not — and names that case's expected fallback or rejection behavior,
so a non-panic alone is not acceptance. The rule is conditional on the
mixed-capability assumption, so it does not bind every shared-stage edit.

`tests/test_skill.py` pins the rule as `_MIXED_CAPABILITY_SHARED_STAGE_RULE` in
`test_brief_requires_a_falsifying_mixed_capability_case`, asserting the
conditional shared-stage sentence, the mixed participant, the expected
fallback-or-rejection behavior, and the non-panic clause. The guard rejects the
pre-change reference, where the four substrings are absent, so it fails when the
rule is removed rather than passing vacuously. No separate falsification fixture
is required, matching the entered-gate precedent, because this is a reference
contract string rather than a source-text negative assertion.

Focused test: `uv run pytest tests/test_skill.py -k "mixed_capability or
entered_directory"` passed (2 passed). `make test` passed: `uv run ruff check`,
`uv run mypy`, the Python suite (723 passed, 3 skipped), and the `install` and
`worktree-parallel` shell suites all green. No `context_rev` bump: the rule is
new guidance for future briefs, no consumer pins this node, and no consumer
assumption changes.
