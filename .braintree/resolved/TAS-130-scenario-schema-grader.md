---
context_rev: 1
priority: P1
updated: 2026-09-13T15:50:18Z
summary: Define one scenario schema and deterministic grading interface for the gold corpus.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-129-benchmark-claim-contract]] at context_rev 2.

# Outcome

One versioned scenario format represents observable repository state, unavailable episodes, memory inserts, task cues, minimal gold evidence, acceptable actions, and deterministic or executable grading across all benchmark families.

# Done when

- The schema records case identity, family, source revision, observable paths, episode order, gold evidence, task, allowed actions, expected outcome, severity, grader, and split metadata.
- The format distinguishes information used to construct memory from information visible at query time.
- A minimal fixture demonstrates each causal arm without arm-specific answers in the task prompt.
- Parser and grader interface tests reject missing evidence, ambiguous outcomes, invalid paths, and unsupported schema versions.

# Result

`src/braintree/memory_scenario.py` freezes the scenario format as one
JSON-serializable record, `memory-scenario-v1`, and imports every literal it
shares with the frozen contract instead of restating it: the nine scenario
families (with their four curation groups), the `development`/`held-out`
splits, the five canonical arm ids, the `action-correctness` primary endpoint,
the correctness-before-cost gate, and the version-pin list.

A scenario records case identity, family, split, severity, source revision, the
memory-construction episodes (`id`, `sequence`, `kind`, `statement`, and
repository-relative `evidence` paths), the query-time `task`,
`observable_paths`, and `allowed_actions`, and the `grading` block
(`action-exact` or `action-acceptable` with expected and acceptable actions and
source-cited `gold_evidence`). The construction block and the query block are
separate by construction, so no gold evidence is visible at query time.

`parse_scenario()` rejects an unsupported schema version, a malformed or
ambiguous record, a missing or unsourced evidence citation, and a non
repository-relative path. `grade()` scores an action against the primary
endpoint with severity-weighted regret, and `cost_eligible()` admits a sample
only after it passes its case grader. `arm_fixtures()` renders the minimal case
once per arm with the task, paths, and allowed actions held fixed and only the
construction input and query-time memory varying. `verify()` checks the schema
against the contract and the fixture round-trip.

Evidence: `tests/test_memory_scenario.py` (25 tests) pins the schema version,
the imported contract literals, the fixture round-trip, the
construction/query separation, the arm-neutral fixtures, the grader and cost
gate, the parser's rejections, tamper detection for arm and family-partition
drift, and the prose document's agreement with every family, arm, severity, and
grader id. `research/agent-memory-scenario-schema.md` is the prose authority and
states the same literals. `ruff check`, `mypy`, and
`pytest tests/test_memory_scenario.py` (25 passed) pass; the schema and its
tests make zero live model calls.
