---
status: resolved
context_rev: 2
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Add a bounded localized-red timeout repair branch.
---

Parent [[TAS-180-usage-feedback-hardening-round-ten]].

# Context

Hekate `FBK-031` finding 3 at `0.6.0+g169bad5`. Round eight
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

# Result

`references/coordination.md` gains a localized-red bullet in `## Timed-out
worker recovery`, between the green and unknown/non-localized red branches. It
authorizes a narrow repair only on established evidence — a reproducible
failure, causal localization to the intended change, an understood cause and
repair write set, and green remaining touched gates — retaining the partial
slice and recording the evidence, the bounded repair brief, and the branch
taken; incomplete evidence falls back to the existing revert-and-re-scope
branch, which is preserved unchanged.

`tests/test_skill.py` adds `_LOCALIZED_RED_RECOVERY_RULE` and
`test_localized_red_timeout_repair_is_stated`, pinning the branch and its
evidence conditions against `references/coordination.md`. `pytest tests/test_skill.py
-k "localized_red or timed_out_worker_recovery"` passes (3 passed). `make test`
passes.
