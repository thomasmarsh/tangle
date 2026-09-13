---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: State how a worker corrects a claimed node whose recorded premise is factually wrong, and who corrects the parent.
next: State the premise-correction rule in the read-and-execute loop and record corrected premises in the node Result.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-016` at `0.6.0+g3bacaf5`: a claimed node's `# Outcome` asserted that
a time-of-impact query was not on the tick path, and validating it against the
code showed it was reached every tick. `SKILL.md` covers summary/next/status
edits, `context_rev` semantics, and escalation of a landed seam another node owns,
but states no rule for "the recorded premise I was handed contradicts the code",
and no rule for whether correcting a recorded premise is consumer-relevant.

# Outcome

`SKILL.md`'s read-and-execute loop states that a worker who finds a recorded
premise or `# Outcome` statement wrong records the corrected state with evidence
in `# Result`, bumps `context_rev` only when a pinned consumer relied on the
premise, and escalates only when the correction would change the declared scope,
outcome, or `Done when`; it also names who corrects the same wrong premise when
the parent repeats it.

# Done when

- The rule is in `SKILL.md` and pinned by `tests/test_skill.py` or an equivalent
  contract test.
- The rule distinguishes a factual premise correction from a scope change.
- Parent-premise correction ownership is explicit.
- `braintree check` and `make test` pass.
