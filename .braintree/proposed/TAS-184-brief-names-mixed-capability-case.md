---
context_rev: 1
priority: P2
updated: 2026-09-14T11:20:50Z
summary: Name an adversarial mixed-capability acceptance input in a shared-stage brief.
next: Add the mixed-capability acceptance-input rule to the brief guidance and pin it with a contract test.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Tangle `FBK-031` finding 7 at `0.6.0+g169bad5`. A leaf changed a shared stage's
maneuver resolution so every route-state agent was assumed to carry a target
clearance; a v2 scenario mixing a lateral mode with a lateral-incapable mode on
one facility panicked, and the existing tests never exercised the mix. No brief
rule requires an adversarial mixed-capability input. `rg -in
'adversarial\|mixed-capability\|shared stage\|acceptance input' SKILL.md
references/` matches nothing.

# Outcome

`references/coordination.md` or `references/authoring.md` requires a brief for a
shared-stage invariant change to name an adversarial acceptance input in which an
existing participant does not carry the new state.

# Done when

- The brief guidance names the mixed-capability adversarial acceptance input for
  a shared-stage invariant change.
- A contract test in `tests/test_skill.py` pins the rule.
- `make test` passes.
