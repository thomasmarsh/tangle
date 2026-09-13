---
context_rev: 1
priority: P1
updated: 2026-09-13T14:36:01Z
summary: Freeze 15 balanced retain, update-existing, and discard admission gold cases with an independent review.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-130-scenario-schema-grader]] at context_rev 1.

# Outcome

Ten to fifteen reviewed admission cases test whether agents retain decision-relevant history without duplicating cheap authoritative state or overgeneralizing transient observations.

# Done when

- Cases balance retain, update-existing, and discard labels.
- Inputs include current code facts, expensive derived results, user constraints, rejected alternatives, repeated gotchas, transient failures, and unsupported hypotheses.
- Every label names the later decision it can affect or why no durable value exists.
- Duplicate-target cases identify the correct existing node and new-memory cases identify an appropriate type and scope.
- An independent review records disagreements before the cases are frozen.

# Result

`benchmark/memory-corpus/admission.json` is the frozen admission-family
corpus: one `memory-admission-corpus-v1` envelope holding 15
`memory-scenario-v1` cases curated at revision `86d81e3` from Braintree's own
history, direct owner directives, and open program questions.

- Label balance is exactly five retain, five update-existing, and five discard;
  each label contributes three `development` and two `held-out` cases.
- The input kinds the Done-when names are all covered: current code facts,
  expensive derived results, user constraints, rejected alternatives, repeated
  gotchas, transient failures, and unsupported hypotheses, plus routine
  narration and duplicate source material as distinct discard cases.
- The label is the expected action's verb (`retain-`/`update-`/`discard-`), so no
  schema field was added and `src/braintree/memory_scenario.py` is unchanged.
- Every update-existing case names the node that already owns the rule
  ([[TAS-009-semantic-revisions]], [[TAS-110-fast-default-test-suite]],
  [[TAS-118-resolved-seam-internal-reuse]], [[TAS-112-timestamp-clamp-rule]],
  [[TAS-116-status-move-staging]]), and every retain case is a fact the
  repository does not record.
- `research/agent-memory-admission-cases.md` is the prose authority, including
  the independent review record.

Evidence: `tests/test_memory_admission_corpus.py` (12 tests) enforces the
envelope, schema conformance, the 5/5/5 label balance, three/two split balance
per label, input-kind coverage, evidence-path existence, arm-neutral tasks, and
document agreement. Independent fresh-context reviews blocked the first draft
and the second pass; every finding is dispositioned in the review record.
Targeted `ruff check`, `mypy`, and `pytest
tests/test_memory_admission_corpus.py tests/test_memory_scenario.py` (37 passed)
pass; the corpus makes zero live model calls.
