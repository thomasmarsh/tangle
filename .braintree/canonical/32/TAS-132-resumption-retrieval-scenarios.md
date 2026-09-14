---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Curate cold-resumption and implicit-retrieval cases with executable next actions.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-130-scenario-schema-grader]] at context_rev 1.

# Outcome

Ten to fifteen reviewed cases test whether a fresh agent can recover decision-changing memory from vague or paraphrased cues and take the correct next engineering action.

# Done when

- Cases cover interruption after a decision, partial implementation, blocker, failed experiment, and handoff.
- At least half use cues with low lexical overlap to the gold memory.
- Each case names minimal gold evidence, relevant distractors, an executable or deterministic outcome, and acceptable alternative actions.
- Memory-irrelevant controls can be solved from current repository state alone.
- Cases do not expose node IDs or gold vocabulary in the task prompt unless that is the behavior under test.

# Result

`benchmark/memory-corpus/resumption.json` (7 cases) and
`benchmark/memory-corpus/implicit-retrieval.json` (8 cases) freeze the two
resumption-and-implicit-retrieval families as `memory-scenario-v1` cases
curated at revision `b8cd7d5` from Braintree's own history.

- All five Done-when interruption kinds are covered — interruption after a
decision, partial implementation, blocker, failed experiment, and handoff —
plus three memory-irrelevant controls. The case id carries the kind and the
test pins the mapping.
- Twelve of fifteen cases are low lexical overlap (at most two shared content
words between the task and the gold evidence); all eight implicit-retrieval
cases qualify.
- Every case names minimal gold evidence, at least one unreferenced distractor
episode, and a deterministic outcome; three use `action-acceptable` because
more than one next action is genuinely correct.
- A control's gold cites only observable paths, and a memory-required case's
gold cites at least one path outside them; the test pins the surfaces that must
never be observable for the six cases the review found leaking.
- `research/agent-memory-resumption-cases.md` is the prose authority, including
the interruption-kind taxonomy, the low-overlap definition, the control
convention, and an independent review record.

Evidence: `tests/test_memory_resumption_corpus.py` (16 tests) enforces the
envelopes, schema conformance, kind coverage, the exact low-overlap set, the
forbidden-observable fix, the distractor rule, the control versus
memory-required property, evidence-path existence, arm-neutral tasks,
declared-action grading, and document agreement. Two independent fresh-context
reviews blocked the first drafts on observable-path answer leakage and returned
accept after the fixes. `make test` passes (442 passed, 3 skipped, 79
deselected); `ruff` and `mypy` pass; the corpora make zero live model calls.
