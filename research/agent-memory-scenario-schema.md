# Memory-evaluation scenario schema

This document is the prose authority for the gold-corpus scenario format and
grader interface of the Tangle memory-evaluation program. The
machine-readable half is [`src/tangle/memory_scenario.py`](../src/tangle/memory_scenario.py),
which imports every shared literal from the frozen contract in
[`src/tangle/memory_contract.py`](../src/tangle/memory_contract.py) rather
than restating it. The module is the single source of truth; this prose must
not drift from it.

Schema version: `memory-scenario-v1`. Everything here is offline. The schema,
its validator, and its tests make **zero live model calls**; a live or paid run
still needs the owner authorization recorded in the contract first.

## 1. One case, one record

A gold case is one versioned JSON document. It records:

| Field | Meaning |
|---|---|
| `schema_version` | the scenario format version; must equal `memory-scenario-v1` |
| `case_id` | stable lowercase slug case identity |
| `family` | exactly one of the nine scenario families |
| `split` | `development` or `held-out`; held-out is the only confirming split |
| `severity` | `minor`, `moderate`, `major`, or `critical`, ordering decision regret |
| `source_revision` | the frozen repository revision the case was curated from |
| `construction.episodes` | ordered historical evidence unavailable at query time |
| `query.observable_paths` | repository-relative paths every arm may read at query time |
| `query.task` | the single arm-neutral task prompt |
| `query.allowed_actions` | the actions the agent may take |
| `grading.grader` | the deterministic scoring rule id |
| `grading.expected_outcome` | the canonical correct action |
| `grading.acceptable_actions` | actions that score full credit |
| `grading.gold_evidence` | the minimal memory the case requires and its sources |

## 2. Construction versus query-time visible information

The schema separates the two information sets the contract's causal arms
depend on. `construction` holds the ordered episodes a memory system may write
from: each episode has a unique `id`, a contiguous 1-based `sequence`
(`sequence` must continue the 1-based episode order), a `kind` (`observation`,
`decision`, `action`, `result`, `failure`, or `feedback`), a `statement`, and
non-empty repository-relative `evidence` paths.

`query` holds only what *every* arm sees, memory or not: the task prompt, the
observable repository paths, and the allowed actions. A memory arm adds its own
retrieved memory; no arm rewrites the task or the allowed actions. The minimal
fixture demonstrates all five arms from one case, and the task prompt never
names an arm-specific answer.

## 3. Gold evidence and grading

`grading.gold_evidence` is the minimal memory the case requires. Each item has
an `id`, a `statement`, and non-empty `source_episodes` naming declared episode
ids, so evidence is traceable to the history that supports it. A case with no
gold evidence is rejected: a case that cannot name the memory it needs is not a
memory case.

The grader is deterministic and scores the contract's primary endpoint,
`action-correctness`:

- `action-exact` admits exactly one acceptable action, the expected outcome;
  any other acceptable set is an ambiguous outcome and is rejected.
- `action-acceptable` admits the declared acceptable actions, which must be a
  subset of the allowed actions and must include the expected outcome.

An unknown grader id, an expected outcome outside the allowed actions, an
acceptable action outside the allowed actions, and an evidence citation to an
unknown episode are all parse failures.

## 4. Contract conformance

The schema imports, rather than restates, the contract's:

- nine scenario families partitioned across the four curation groups:

| Curation group | Families |
|---|---|
| `admission` | `admission` |
| `resumption-and-implicit-retrieval` | `resumption`, `implicit-retrieval` |
| `revision-and-conflict` | `temporal-update`, `cascading-invalidation`, `conflict-and-uncertainty` |
| `transfer-interference-and-authority` | `experience-transfer`, `forgetting-and-interference`, `poisoning-and-authority` |

- `development` and `held-out` splits;
- five causal arms (`repository-only`, `raw-history`, `flat-memory`,
  `tangle`, `oracle`);
- `action-correctness` primary endpoint;
- correctness-before-cost gate: a sample enters cost summaries only after it
  passes its case grader, so an incorrect cheap arm never wins;
- version-pin list: protocol, corpus-digest, fixture-version, source-revision,
  model, model-revision, reasoning-effort, prompt-revision, tool-revision,
  budget, allowed-commands, and grader-version.

`scenario_document()` emits the whole record as JSON, `parse_scenario()`
validates it, `grade()` scores an action, `cost_eligible()` applies the
correctness gate, and `verify()` returns the schema's structural
inconsistencies. `tests/test_memory_scenario.py` protects the version,
rejections, arm neutrality, and the document's agreement with the module.
