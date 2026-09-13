# Memory-evaluation admission cases

This document is the prose authority for the **admission** family of the
Braintree memory-evaluation gold corpus. The machine-readable half is
[`benchmark/memory-corpus/admission.json`](../benchmark/memory-corpus/admission.json);
the case format is owned by
[`src/braintree/memory_scenario.py`](../src/braintree/memory_scenario.py) and
[`research/agent-memory-scenario-schema.md`](agent-memory-scenario-schema.md),
which this document must not restate. The corpus is offline: parsing, grading,
and its tests make **zero live model calls**, and any live or paid run still
requires the owner authorization recorded in
[`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md).

TAS-131 curates this family. TAS-132, TAS-133, and TAS-134 curate the other
eight families, and TAS-135 owns whole-corpus validation, deterministic splits,
the corpus digest, and the leakage audit.

## 1. Corpus conventions

The file is one versioned envelope:

| Key | Meaning |
|---|---|
| `corpus_version` | `memory-admission-corpus-v1`, the envelope format |
| `schema_version` | `memory-scenario-v1`, the case format version |
| `family` | `admission`, the only family this file may contain |
| `source_revision` | `86d81e3`, the one frozen revision every case's observable state is read at |
| `cases` | the 15 scenario records |

Every case conforms to the scenario schema unchanged. No case carries a bespoke
field: the schema's parser drops unknown keys, so an admission-specific field
would not survive a round trip.

**The admission label is the expected action's verb.** A case's label is
derived mechanically from `grading.expected_outcome`:

| Prefix | Label | Meaning |
|---|---|---|
| `retain-` | retain | write a new durable memory |
| `update-` | update-existing | attach the observation to a node that already owns it |
| `discard-` | discard | admit nothing; the observation has no durable value |

`allowed_actions` names the label's decision beside plausible wrong decisions a
naive agent would choose. The task prompt never names the answer or any action,
so the choice among the visible actions is the experiment.

**Splits.** Each label contributes three `development` and two `held-out`
cases, so every label appears in both splits. TAS-135 freezes the deterministic,
stratified split; variants of one source incident never span the two splits.

**Retention means the fact is unrecorded.** A `retain-` case is valid only when
the repository does not already record the retained fact: if a node, the skill,
or a source comment owns it, the correct action is `update-` or `discard-`.
The gold evidence carries the retained fact, and the harness must exclude the
corpus file from every arm's readable state (TAS-135's leakage audit). The
admission family draws its retained facts from the two places a repository
structurally cannot record: direct owner directives, and open curator
predictions about work that has not run yet.

Every `retain-` and `update-` case keeps the node that owns the fact or rule
out of `query.observable_paths`, so the correct action requires retrieval; the
`discard-` cases are the family's intentional memory-irrelevant controls.

**Evidence citations.** The scenario schema requires each construction episode
to cite repository-relative evidence. Episodes that originate in owner dialogue
or curator reasoning cite the repository surface where the resulting memory
would live, because the dialogue itself has no path; the gold evidence, not the
citation, carries the unavailable content.

**Input kinds.** The corpus covers the seven input kinds the TAS-131 Done-when
names — current code fact, expensive derived result, user constraint, rejected
alternative, repeated gotcha, transient failure, and unsupported hypothesis —
and adds routine narration and duplicate source material as distinct discard
cases.

## 2. Cases

`Target` names the existing node for an `update-existing` case and the type and
scope for a new-memory `retain-` case.

| Case | Label | Input kind | Severity | Split | Justification | Target |
|---|---|---|---|---|---|---|
| `admission-retain-owner-compression-constraint-001` | retain | user constraint | major | development | An owner directive against reintroducing context compression without measured net savings is recorded nowhere and governs later tooling decisions. | new owner constraint (tooling, repository scope) |
| `admission-retain-offline-grading-constraint-001` | retain | user constraint | moderate | development | The requirement that no evaluation case require the optional semantic extra is stronger than the manifest's optional declaration and is unrecorded. | new owner constraint (evaluation, repository scope) |
| `admission-retain-heldout-separation-hypothesis-001` | retain | unsupported hypothesis | major | held-out | An untested prediction that the held-out split separates arms more strongly than development precedes any re-split decision. | new `THO` question (split separation, program scope) |
| `admission-retain-label-stability-hypothesis-001` | retain | unsupported hypothesis | minor | development | An untested prediction that the derived label stays stable precedes any decision to add an explicit label field. | new `THO` question (schema evolution, corpus scope) |
| `admission-retain-envelope-layout-alternative-001` | retain | rejected alternative | moderate | held-out | The rejected per-case file layout and its per-family-unit rationale are unrecorded and prevent re-litigating the corpus format. | new `DEC` (corpus layout, program scope) |
| `admission-update-existing-context-rev-001` | update-existing | repeated gotcha | moderate | development | A rule clarification that recurred on a later round belongs to the node that already owns the rule. | `TAS-009-semantic-revisions` |
| `admission-update-existing-fast-suite-001` | update-existing | expensive derived result | minor | held-out | A re-measured suite runtime is new evidence for the node that owns the fast-suite outcome. | `TAS-110-fast-default-test-suite` |
| `admission-update-existing-seam-reuse-001` | update-existing | repeated gotcha | moderate | held-out | A matching reuse question extends the node that already owns the visibility-widening rule. | `TAS-118-resolved-seam-internal-reuse` |
| `admission-update-existing-clamp-rule-001` | update-existing | repeated gotcha | minor | development | A report about the clamp rule that arrived again after the rule landed adds recurrence evidence to the owning node. | `TAS-112-timestamp-clamp-rule` |
| `admission-update-existing-staging-gotcha-001` | update-existing | repeated gotcha | major | development | A recurrence of the `git mv` staging failure extends the node that already owns the staging rule. | `TAS-116-status-move-staging` |
| `admission-discard-current-code-fact-001` | discard | current code fact | minor | development | The interpreter floor and the empty dependency list are authoritative in the manifest and cheaply observable; no durable value exists. | none — duplicate current state |
| `admission-discard-transient-failure-001` | discard | transient failure | minor | held-out | A single unreproduced timeout has no measured cause, so it cannot change a future decision. | none — transient |
| `admission-discard-cache-speculation-001` | discard | unsupported hypothesis | moderate | development | An unmeasured claim that a cache is too small cannot change a decision until it has a size measurement or a scaling test. | none — unsupported |
| `admission-discard-routine-verification-001` | discard | routine narration | minor | held-out | A repeated passing run is routine narration, which the admission policy excludes and version history already records. | none — routine narration |
| `admission-discard-duplicate-source-001` | discard | duplicate source material | minor | development | The contract and its prose authority already state the partition, so a restatement duplicates source material. | none — duplicate source |

## 3. Independent review

An independent reviewer that did not author the corpus reviewed every case
against the TAS-131 Done-when before the cases were frozen. The review returned
a blocking verdict on the first draft, and every finding was dispositioned.

### Review record

- **Reviewer:** independent fresh-context review, 2026-09-13.
- **Verdict:** block on the first draft and on the second pass's observable-path and task-leak findings; all findings fixed before freeze.

| # | Reviewer finding | Disposition |
|---|---|---|
| 1 | `retain-new-decision-node-001` was verbatim the outcome of the already-resolved `TAS-118`, so `retain` duplicated an owner. | Removed; the retain set was rebuilt from facts the repository does not record. |
| 2 | `update-existing-seam-rule-001` was retargeted to `TAS-117` although the reuse question is `TAS-118`'s subject. | Retargeted to `TAS-118-resolved-seam-internal-reuse`. |
| 3 | `retain-rejected-alternative-001` duplicated `DEC-002`'s recorded B-tree rejection. | Removed; `DEC-002` already owns that rejection. |
| 4 | `retain-repeated-gotcha-001` duplicated `TAS-116` and the skill's staging sentence. | Reclassified as `update-existing` targeting `TAS-116`. |
| 5 | `retain-embedding-selection-001` duplicated `TAS-089` and proposed `THO` for a settled choice. | Removed; `TAS-089` owns the runtime verdict. |
| 6 | `discard-unsupported-hypothesis-001` claimed no bound existed, but `index.py` sets `@lru_cache(maxsize=4096)`. | Restated as a cache-size speculation with no scaling measurement. |
| 7 | `retain-user-constraint-001` cited `AGENTS.md`, which does not state the constraint, and `pyproject.toml`/`README.md` restated it. | Replaced with owner constraints the repository does not record. |
| 8 | Input-kind coverage was inflated (five cases claimed "repeated gotcha"; routine narration was labelled a code fact). | Re-derived the per-case mapping; the guard now requires honest per-case kinds and only subset coverage of the seven required kinds. |
| 9 | The prose claimed three development and two held-out per label, but discard was 2/3 and the totals were 8/7. | Corpus and prose both set to three development and two held-out per label. |
| 10 | Four task prompts leaked the answer ("whose rule has already landed", "repeated routine verification", "restates the frozen contract partition", "speculation"). | Task prompts neutralized. |
| 11 | The prose said the other three families; the corpus should say the other eight. The routine case's "356" figure came from `TAS-110`, not the `Makefile`. | Corrected; the routine episode no longer cites the test count. |
| 12 | `source_revision` `86d81e3` could not be verified with read-only tools, and a benchmark file records a different revision. | Verified that `86d81e3` exists and contains the cited nodes; the frozen revision is the pre-corpus commit, and the corpus file is excluded from observable state. |
| 13 | Second pass: four `update-` cases listed the owning node or the rule-bearing `SKILL.md`/`references/coordination.md` in `observable_paths`, so they were solvable without memory. | The owning node and rule text were removed from `observable_paths`; those cases now require retrieval. |
| 14 | Second pass: three task prompts still leaked the answer ("matches an existing rule", "repeated report about an existing rule", "restated revision rule"). | Prompts neutralized. |
| 15 | Second pass: the offline-grading constraint was substantially recorded in the contract already. | Narrowed to the unrecorded rule that no case may *require* the optional semantic extra. |
| 16 | Second pass: the guard asserted at least two per split while the prose claimed exactly three/two. | The guard now asserts exactly three development and two held-out per label. |
| 17 | Second pass: the `context_rev` case's episode was a single restatement, not a recurrence. | Rewritten as a genuine later recurrence so the `repeated gotcha` kind is honest. |

## 4. Validation

`tests/test_memory_admission_corpus.py` enforces the envelope, schema
conformance of every case, the 5/5/5 label balance, three/two split balance per
label, the required input-kind coverage, evidence-path existence, arm-neutral
tasks, and agreement between this document and the corpus.

This test is the admission family's guard only. TAS-135 replaces it with the
whole-corpus offline validator, deterministic splits, corpus digest, and
leakage audit that the TAS-121 outcome requires.
