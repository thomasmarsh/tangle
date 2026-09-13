---
context_rev: 1
priority: P1
updated: 2026-09-13T16:16:48Z
summary: Redesign the gold corpus so memory-required cases separate repository-only from oracle.
next: Repair or replace the seven non-separating development cases and re-run the bounded pilot.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-136-pilot-separability-audit]] at context_rev 2.

The pilot found the repository-only floor too high: for seven of nine
memory-required development cases the expected or an acceptable action is
inferable from the task, observable files, and allowed actions without the
unavailable history. The remediation is a corpus redesign, not a harness change:
a case needs distractors that are locally plausible and that only the deciding
history disambiguates.

# Outcome

A revised gold corpus whose memory-required cases fail from observable state
alone while the oracle evidence makes the intended action attainable, verified
by a re-run of the bounded separability pilot.

# Done when

- Every non-separating case is repaired with a recorded reason or replaced by a development case that separates.
- The corpus keeps its 40–60-case range, family and curation-group balance, control balance, deterministic split, and digest.
- The bounded separability pilot is re-run on a preregistered development subset and separates.
- `braintree check` and `make test` pass.
