# Memory-evaluation resumption and implicit-retrieval cases

This document is the prose authority for the **resumption** and
**implicit-retrieval** families of the Braintree memory-evaluation gold corpus.
The machine-readable halves are
[`benchmark/memory-corpus/resumption.json`](../benchmark/memory-corpus/resumption.json)
and
[`benchmark/memory-corpus/implicit-retrieval.json`](../benchmark/memory-corpus/implicit-retrieval.json);
the case format is owned by
[`src/braintree/memory_scenario.py`](../src/braintree/memory_scenario.py) and
[`research/agent-memory-scenario-schema.md`](agent-memory-scenario-schema.md),
which this document must not restate. The corpus is offline: parsing, grading,
and its tests make **zero live model calls**, and any live or paid run still
requires the owner authorization recorded in
[`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md).

TAS-132 curates these two families. TAS-131 curated admission, TAS-133 and
TAS-134 curate the remaining families, and TAS-135 owns whole-corpus
validation, deterministic splits, the corpus digest, and the leakage audit.

## 1. Corpus conventions

Each family is one versioned envelope, because the layout decision is one
envelope per family so a family can be digested, split, and reviewed as a unit.

| File | `corpus_version` | `family` | Cases |
|---|---|---|---|
| `resumption.json` | `memory-resumption-corpus-v1` | `resumption` | 7 |
| `implicit-retrieval.json` | `memory-implicit-retrieval-corpus-v1` | `implicit-retrieval` | 8 |

Both envelopes carry `schema_version: memory-scenario-v1` and the one frozen
`source_revision` `b8cd7d5`, the commit the observable state is read at. Every
case conforms to the scenario schema unchanged; no case carries a bespoke field,
because the schema's parser drops unknown keys.

**Both families answer one question: what is the correct next engineering
action?** The resumption family resumes interrupted work; the implicit-retrieval
family starts from a paraphrase that shares little vocabulary with the memory
that decides it. A case's `expected_outcome` is the acceptable next action and
`grading.gold_evidence` is the minimal memory that decides it.

### Interruption kinds

Every case tests one interruption kind. The resumption cases carry the kind in
the case id; the test pins the mapping so coverage cannot silently disappear.

| Kind | Meaning |
|---|---|
| `after-decision` | A settled decision constrains the proposed next action. |
| `partial-implementation` | A change landed incompletely; the remaining step is not the obvious one. |
| `blocker` | The next step needs state no node owns, such as owner authorization. |
| `failed-experiment` | An approach was measured and rejected; a proposal would repeat it. |
| `handoff` | An agent continues work another agent stopped and must recover the route. |
| `control` | No unavailable history is required; current observable state answers the task. |

### Low lexical overlap

A case is **low lexical overlap** when its task prompt shares at most two
content words with the union of its gold-evidence statements, after removing
stopwords and single-character tokens. The implicit-retrieval family exists to
test paraphrase and synonym cues, so all eight of its cases are low overlap;
four resumption cases also qualify (three memory-required cases and the
resumption control). That is twelve of fifteen cases, above the "at least half"
bar, while the remaining cases deliberately keep recognizable domain
vocabulary. The test pins the exact low-overlap set.

### Controls

A **control** case is memory-irrelevant: its gold evidence is a current-state
fact that also appears in `query.observable_paths`, so a repository-only arm can
answer it. Every family includes controls so a system cannot score by always
consulting memory. The test enforces the structural half: a control's
gold-referenced episodes cite only observable paths, and every memory-required
case's gold cites at least one path outside `observable_paths`.

### Distractors

Each case carries at least one **distractor** episode — plausible related
history that no gold evidence references — and the allowed actions include
wrong next actions. The gold evidence cites only the episodes that decide the
action, so a reader can separate the minimal memory from the surrounding noise.
The test asserts that every case has at least one unreferenced episode; whether
that episode is *relevant* is a curation judgment recorded per case in the
tables above, not a structural check.

### Acceptable alternatives

Three cases use `action-acceptable` because more than one next action is
genuinely correct: adding a dry-run preview beside an in-place migration,
inspecting or waiting out a lease before reclaiming, and reporting or routing a
stale parent pointer. The rest use `action-exact`, where only one action is
correct.

## 2. Cases

### Resumption

| Case | Kind | Severity | Split | Cue | Gold memory | Distractor |
|---|---|---|---|---|---|---|
| `resumption-after-decision-shared-install-001` | after-decision | major | development | Follow the packaging guide and give each project its own copy so it can pin a version | The shared install is deliberate; per-project copies duplicate and drift, and the revision stamp reports the version | Installed-revision stamp |
| `resumption-after-decision-semantic-optional-001` | after-decision | major | held-out | Make embedding similarity the default near-duplicate check | Embeddings lost near-duplicate retrieval and stay optional and advisory | Dependency-free default install |
| `resumption-partial-implementation-vault-notice-001` | partial-implementation | moderate | development | Refuse to write when the resolved vault differs from the named one | The in-place migration is deliberate; announce it rather than refuse it | Legacy reservation merge |
| `resumption-blocker-live-authorization-001` | blocker | critical | development | Record the two matched live token samples now | Live or paid runs need owner authorization recorded before execution | Session-parser reuse |
| `resumption-failed-experiment-cold-resume-rule-001` | failed-experiment | major | held-out | Add a header-first cold-resume instruction | The cold-resume rule raised tokens 26.6% and was rejected | `Reading`-prefix parser repair |
| `resumption-handoff-corpus-continuation-001` | handoff | major | held-out | Continue the corpus after admission landed | The next route is resumption and implicit-retrieval curation | Schema needs no per-family field |
| `resumption-control-vault-rename-001` | control | minor | development | Revert the `nodes/` to `.braintree/` rename | Current state and the resolved decision already settle it | Legacy in-place migration |

### Implicit retrieval

| Case | Kind | Severity | Split | Cue | Gold memory | Distractor |
|---|---|---|---|---|---|---|
| `implicit-retrieval-failed-experiment-embedding-default-001` | failed-experiment | major | development | Let "sounds similar" become the main repeated-work check | Similarity search lost to the lexical baseline and stays advisory | Dependency-free default install |
| `implicit-retrieval-after-decision-seam-reuse-001` | after-decision | moderate | development | Decide whether a slice may widen a completed sibling's private helper | An internal, behavior-preserving reuse is authored without escalation and recorded in the worker's result | Non-behavioral reuse did not bump its owner's revision |
| `implicit-retrieval-blocker-lease-handoff-001` | blocker | moderate | held-out | Hand an abandoned job to another agent right now | A lease has a 900-second default, renews, and distinguishes expiry | Different-agent `no-op` |
| `implicit-retrieval-failed-experiment-orientation-compaction-001` | failed-experiment | moderate | held-out | Collapse the repeated summary instructions into a shorter loop | Orientation-loop compaction was measured higher and rejected | No recording-pipeline failure |
| `implicit-retrieval-handoff-parent-next-001` | handoff | major | held-out | Finish a child while the parent pointer still names it | The coordinator owns the advance; the worker reports the stale route | Checker silence for action `next` |
| `implicit-retrieval-partial-implementation-write-set-closure-001` | partial-implementation | moderate | development | Finish the change in a neighboring module and golden | The write set is the change's compile-and-golden closure | Minimal primitive authoring |
| `implicit-retrieval-control-version-declaration-001` | control | minor | development | Where the bumped version number lives | Current state declares it once in `pyproject.toml` | One declared version bumps |
| `implicit-retrieval-control-offline-gate-001` | control | minor | held-out | Which check to run before committing | Current state runs one offline gate with benchmarks opt-in | Cumulative token telemetry |

## 3. Independent review

An independent fresh-context reviewer that did not author the corpus reviewed
every case against the TAS-132 Done-when before the cases were frozen.

### Review record

- **Reviewer:** two independent fresh-context reviews plus a targeted third-pass re-check, 2026-09-13.
- **Verdict:** the first pass blocked on six observable-path leaks; the second pass blocked on one residual `index.py` leak in the two semantic cases; the third pass accepted after the leak was removed. Every finding was fixed before freeze.

| # | Reviewer finding | Disposition |
|---|---|---|
| 1 | Six memory-required cases leaked the deciding fact through `observable_paths`: the semantic-capability cases observed `semantic.py`/`clustering.py`, the benchmark-opt-in cases observed `tests/test_quality_benchmark.py`, the lease case observed `cli.py`, and the vault case observed `README.md`. | Replaced each observable set with a task-grounding surface that does not state the decision (`quality_benchmark.py`, `feedback_record.py`, `SKILL.md`, and `tests/test_bt_index.py` for the semantic cases) and pinned the forbidden surfaces in `_FORBIDDEN_OBSERVABLE`. Residual status-quo bias is deferred to TAS-135's leakage audit. |
| 2 | `implicit-retrieval-blocker-lease-handoff-001` ep-2 cited `SKILL.md`, which does not state the 900-second lease. | Retargeted ep-2 to `references/coordination.md` and `src/braintree/sidecar.py`. |
| 3 | The benchmark episodes cited test files that do not state the 83-second runtime or the marker exclusion. | Added `.braintree/resolved/TAS-110-fast-default-test-suite.md` and `pyproject.toml` to the relevant episodes. |
| 4 | `resumption-handoff-corpus-continuation-001` ep-3 misattributed the gating: `TAS-133` is gated on `TAS-130`, not on resumption. | Cited `TAS-121` as the coordinating node and dropped the revision-and-conflict gating clause. |
| 5 | The prose counted two low-overlap resumption cases; three memory-required resumption cases plus the control qualify. | Corrected to twelve of fifteen and pinned the exact low-overlap set in the test. |
| 6 | The prose claimed every case carries a distractor, but the three controls did not. | Added a distractor episode to each control and a test that every case has an unreferenced episode. |
| 7 | `implicit-retrieval-failed-experiment-orientation-compaction-001` ep-3 cited `THO-004` for a resumable-action claim it does not make. | Rewrote ep-3 to `THO-004`'s actual recording-pipeline statement and corrected its distractor cell. |
| 8 | The review record was an unfilled placeholder. | Filled with this review. |
| 9 | The guards did not enforce the node-id/family-prompt rule, the distractor rule, or the exact low-overlap set. | Added `test_task_prompts_expose_no_node_ids_or_family_names`, `test_every_case_carries_a_distractor_episode`, the forbidden-observable test, and the exact low-overlap-set assertion. |
| 10 | Second pass: the two semantic cases still observed `src/braintree/index.py`, whose `similar` docstring calls the lexical baseline "the correctness reference an admission decision compares a draft against" — the `DEC-006` conclusion. | Moved both observables to `tests/test_bt_index.py`, which exercises near-duplicate ranking without stating the boundary decision, and broadened `_SEMANTIC_DECIDING_SURFACES` to cover every leaky semantic surface. |
| 11 | Second pass: the orientation-compaction distractor cell still described the pre-rewrite claim. | Updated the cell to the recording-pipeline statement. |
| 12 | Second pass: the offline-gate control's second episode restated the first rather than being a related distractor. | Replaced it with the token-telemetry observation. |
| 13 | Third pass (non-blocking): the offline-gate control's distractor cell still named the old episode. | Updated the cell to "Cumulative token telemetry"; the third pass accepted. |

## 4. Validation

`tests/test_memory_resumption_corpus.py` enforces the two envelopes, schema
conformance of every case, the interruption-kind coverage, the low-overlap
count, the control versus memory-required observable-path property, split
population, evidence-path existence, arm-neutral tasks, the declared-action
grading, and agreement between this document and both corpora.

This test is these two families' guard only. TAS-135 replaces it with the
whole-corpus offline validator, deterministic splits, corpus digest, and
leakage audit that the TAS-121 outcome requires.

## 5. Residual repair

The round-three separability pilot
([`research/agent-memory-pilot-v2-preregistration.md`](agent-memory-pilot-v2-preregistration.md))
left `resumption-after-decision-shared-install-001` non-separating:
`repository-only` was correct 3/3 because the correct action, keeping one shared
program, coincided with the generic "avoid duplication" default. The case now
states a locally plausible project packaging guide that requires a broken
project to pin its own copy rather than wait for a shared fix, so the
`repository-only` prior follows the guide and installs a per-project copy. The
unavailable history still decides the other way: the shared install is the
recorded decision, per-project copies were rejected because they duplicate and
drift, and version pinning is handled by the installed-revision stamp. Only the
task text changed; the case id, family, split, severity, gold evidence, allowed
actions, and citations are unchanged, and the corpus digest was re-frozen. The
repaired case still requires a paid separability re-run to prove it separates.
