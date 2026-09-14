---
context_rev: 2
priority: P2
updated: 2026-09-14T11:27:54Z
summary: Add a bounded localized-red timeout repair branch.
next: Define the evidence threshold and bounded write set for localized-red recovery in references/coordination.md and pin them with a test.
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

`references/coordination.md` adds an evidence-bounded localized-red branch to
`## Timed-out worker recovery`: retain the partial slice and authorize a narrow
repair only when the failure is reproducible, localized to the intended change,
its cause and repair write set are understood, and the remaining touched gates
are green. Record that evidence, the bounded repair brief, and the branch taken.
When any condition is not established, retain the existing revert-and-re-scope
branch.

# Done when

- `references/coordination.md` states the localized-red branch beside the green
  and unknown/non-localized red branches.
- The branch requires a reproducible failure, causal localization, a bounded
  repair write set, and green remaining touched gates.
- The fallback remains revert-and-re-scope when that evidence is incomplete.
- A contract test in `tests/test_skill.py` pins the rule.
- `make test` passes.
