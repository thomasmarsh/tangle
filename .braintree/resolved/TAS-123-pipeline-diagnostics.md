---
context_rev: 3
priority: P1
updated: 2026-09-13T19:48:55Z
summary: Attribute benchmark failures to memory writing, retrieval, reading, or action.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-122-causal-baseline-experiment]] at context_rev 3.

The 540-sample five-arm causal result, including 209 labelled failures, is in
`benchmark/memory-causal-result.json`.

# Outcome

Every benchmark failure is attributable to admission, organization or consolidation, retrieval, stale or conflicting evidence, reading and reasoning, or action, so changes target the demonstrated bottleneck.

# Done when

- The taxonomy has mutually distinguishable labels and an adjudication procedure.
- Retrieval evidence and downstream use are scored separately.
- The initial causal samples are labeled with inter-review agreement or explicit disagreements.
- A diagnostic report ranks bottlenecks by frequency and severity and names which later workstreams are justified.

# Result

The pipeline diagnostics are complete. `src/braintree/memory_diagnostics.py`
realizes the contract's six `DIAGNOSTIC_LABELS` as one stage each, scores
retrieval coverage and downstream use separately, and re-derives the committed
report `benchmark/memory-diagnostics-report.json` offline;
`research/agent-memory-pipeline-diagnostics.md` is the prose authority and
`tests/test_memory_diagnostics.py` the contract tests.

The 209 incorrect-action failures attribute as write-miss 80, reader-failure 87,
and action-failure 42, with zero organization-error, retrieval-miss, and
stale-or-conflicting-retrieval. All 80 write-misses are the `repository-only`
floor, so the corpus is memory-required rather than the memory system defective.
Every memory arm delivered every required source: the shared memory budget (8)
exceeds the largest case (5 episodes), so the development run cannot demonstrate
a retrieval miss.

Two independent fresh-context reviewers that did not author the module, the
built-in `reviewer` and an external `codex-exec` reviewer, both rejected the
first draft because `flat-memory` frames each episode as `note N: <statement>`
and an exact-statement match scored all 23 of its failures as retrieval misses.
The match now sees through the note prefix, those failures are downstream, and
`test_flat_memory_and_raw_history_deliver_the_same_episodes` pins the fix. The
reviewers also found the budget-over-corpus saturation, now recorded in the
report's `limits` block.

The committed evidence-priority adjudication agrees with the independent
behaviour-priority reviewer on 191 of 209 failures (0.9139); the 18 explicit
disagreements are all `repository-only` samples that chose a discard action and
are kept as write-miss because no memory was ever delivered. Only TAS-127 is
diagnostically justified (21 poisoning action failures where delivered authority
evidence was discarded); TAS-124, TAS-125, and TAS-126 are not demonstrated on
this development run. The dominant downstream loss is reading or reasoning, not
a memory mechanism.

Residual: the round-five separability pilot returned `revise` after the three
round-four cases were repaired; [[TAS-152-conflict-separability-residual]]
repaired the last non-separating case and its round-seven re-run returned
`proceed`, so the confirmatory freeze no longer carries a separability residual.
