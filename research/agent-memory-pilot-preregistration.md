# Separability-pilot preregistration

This document preregisters the bounded separability pilot that gates the
evaluation foundation before the five-arm causal experiment spends significant
tokens. It is the prose authority for the pilot subset. The machine-readable
half is [`src/braintree/memory_corpus.py`](../src/braintree/memory_corpus.py)
(`pilot_subset`, `pilot_problems`, `PILOT_PROTOCOL`, `PILOT_ARMS`,
`PILOT_VERDICTS`), and
[`tests/test_memory_pilot.py`](../tests/test_memory_pilot.py) pins this document
to it. The evaluation contract and the corpus belong to
[`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md)
and [`research/agent-memory-corpus-validation.md`](agent-memory-corpus-validation.md).

Protocol: `memory-pilot-v1`. The pilot runs **only** on the `development` split;
the frozen `held-out` split is never inspected, so a pilot cannot tune toward a
confirming result.

## 1. Purpose

The pilot checks the corpus's core property before the full experiment: a
memory-required case must not be solvable reliably from the repository state
its query exposes, and the oracle's minimal gold evidence must make the intended
action attainable. It is a bounded two-arm run — repository-only (floor) and
oracle (ceiling) — over a preregistered subset. It is a gate on the evaluation
foundation, not a replacement for the five-arm causal runner.

## 2. Preregistered subset

Twelve development cases: one memory-required case per family plus one
observable-only control from each family that has one. Every family and every
curation group is represented.

| Family | Case | Role |
|---|---|---|
| admission | `admission-retain-label-stability-hypothesis-001` | memory-required |
| admission | `admission-discard-cache-speculation-001` | control |
| resumption | `resumption-after-decision-benchmark-opt-in-001` | memory-required |
| resumption | `resumption-control-vault-rename-001` | control |
| implicit-retrieval | `implicit-retrieval-after-decision-fast-gate-001` | memory-required |
| implicit-retrieval | `implicit-retrieval-control-version-declaration-001` | control |
| temporal-update | `temporal-update-cosmetic-edit-001` | memory-required |
| cascading-invalidation | `cascading-invalidation-independent-evidence-001` | memory-required |
| conflict-and-uncertainty | `conflict-and-uncertainty-competing-rules-001` | memory-required |
| experience-transfer | `experience-transfer-recurring-failure-001` | memory-required |
| forgetting-and-interference | `forgetting-and-interference-irrelevant-growth-001` | memory-required |
| poisoning-and-authority | `poisoning-and-authority-direct-injection-001` | memory-required |

## 3. Selection rule

`memory_corpus.pilot_subset()` derives the subset deterministically from the
frozen corpus, before any run:

1. order each family's development cases by `case_id`;
2. take the first memory-required case, then the first observable-only control
   when the family has one.

A control is a case whose gold evidence cites only `query.observable_paths`
(`memory_corpus.is_control`). Because the rule is a pure function of the frozen
corpus, the corpus digest already pins the subset, and no case can be added or
removed after an outcome is seen. `memory_corpus.pilot_problems()` fails the
subset if it leaves the 8–12 range, drops a family or a curation group, or loses
its required/control mix.

## 4. Arms, grading, and power

Only two of the contract's five arms run: `repository-only` and `oracle`. Every
other fixture input is shared. Each case's action is scored by
`memory_scenario.grade()` against the `action-correctness` endpoint, and the
correctness-before-cost gate admits a sample to cost summaries only after it
passes its case grader. The pilot is exploratory: one repetition per case and
arm, so its result is never confirmatory under the contract's exploratory rule.

## 5. Separation criteria and decision rule

- A memory-required case **separates** when repository-only is graded incorrect
  and oracle is graded correct.
- A control is **valid** when repository-only is graded correct; it must remain
  solvable without oracle evidence.
- A failing case is **repaired or removed** with a recorded reason, without
  inspecting held-out outcomes. A case whose repository-only answer is already
  correct is not memory-required; a case whose oracle answer is incorrect has
  insufficient gold evidence or a reader failure.

The phase-one decision is one of `proceed`, `revise`, or `stop`:

- **proceed** — every retained case meets its criterion and the retained subset
  is still 8–12 development cases spanning every family and curation group.
- **revise** — one or two cases fail but can be repaired or removed while the
  subset keeps its minimum size and four-group coverage.
- **stop** — three or more memory-required cases fail to separate, or repair
  cannot retain the minimum size or four-group coverage.

## 6. Version pins and authorization

A run freezes the contract's pin fields: protocol, corpus digest, fixture
version, source revision, model, model revision, reasoning effort, prompt
revision, tool revision, budget, allowed commands, and grader version. The
reported fixture digest is the corpus digest, which already pins the
deterministic subset. The run records the prompt, the fixture digest, and the
session telemetry (tokens, tool calls, turns, latency).

Live or paid execution is a **separate authorization**: the contract's exact
requirement is

> Live or paid model runs require explicit owner authorization recorded before execution; the contract, scenario schema, gold corpus, validator, and contract tests make zero live model calls.

Until the owner records that authorization, the pilot is blocked and the corpus
validator, this preregistration, and its tests stay zero-live.

## 7. Residuals

- The pilot's decision, each repaired or removed case, and the resulting subset
  are recorded in the pilot task's result.
- Growth size stays a harness knob, as
  [`research/agent-memory-corpus-validation.md`](agent-memory-corpus-validation.md)
  decides; the pilot instantiates no growth scaling.
- Any case repaired during the pilot changes the corpus digest, so the
  subsequent five-arm runner must pin the new digest rather than this one.
