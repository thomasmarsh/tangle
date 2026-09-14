---
context_rev: 1
priority: P2
updated: 2026-09-14T11:20:50Z
summary: Add the localized-red narrow-repair branch to the timed-out worker recovery procedure.
next: Add the localized-red branch to references/coordination.md and pin it with a contract test.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Tangle `FBK-031` finding 3 at `0.6.0+g169bad5`. Round eight
[[TAS-159-timed-out-worker-recovery]] added `## Timed-out worker recovery`, which
the session used: a green partial may be finished by a narrow run or accepted on
the same node, and a non-green partial is reverted and re-scoped. A partial that
is red on one localized, understood case while the rest is green falls in the
second branch, so the blanket revert discards a near-complete slice.

# Outcome

`references/coordination.md` adds the localized-red branch to `## Timed-out
worker recovery`: when the partial state compiles except for one localized,
understood failing case and the rest is green, authorize a narrow repair run that
keeps the partial slice instead of reverting it, and record which branch was
taken and why.

# Done when

- `references/coordination.md` states the localized-red branch beside the green
  and non-green branches.
- A contract test in `tests/test_skill.py` pins the rule.
- `make test` passes.
