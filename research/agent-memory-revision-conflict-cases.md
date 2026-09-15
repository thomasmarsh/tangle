# Memory-evaluation revision-and-conflict cases

This document is the prose authority for the **temporal-update**,
**cascading-invalidation**, and **conflict-and-uncertainty** families of the
Tangle memory-evaluation gold corpus. The machine-readable halves are
[`benchmark/memory-corpus/temporal-update.json`](../benchmark/memory-corpus/temporal-update.json),
[`benchmark/memory-corpus/cascading-invalidation.json`](../benchmark/memory-corpus/cascading-invalidation.json),
and
[`benchmark/memory-corpus/conflict-and-uncertainty.json`](../benchmark/memory-corpus/conflict-and-uncertainty.json);
the case format is owned by
[`src/tangle/memory_scenario.py`](../src/tangle/memory_scenario.py) and
[`research/agent-memory-scenario-schema.md`](agent-memory-scenario-schema.md),
which this document must not restate. The corpus is offline: parsing, grading,
and its tests make **zero live model calls**, and any live or paid run still
requires the owner authorization recorded in
[`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md).

TAS-133 curates these three families. TAS-131 curated admission, TAS-132
curated resumption and implicit retrieval, TAS-134 curates the remaining
families, and TAS-135 owns whole-corpus validation, deterministic splits, the
corpus digest, and the leakage audit.

## 1. Corpus conventions

Each family is one versioned envelope, because the layout decision is one
envelope per family so a family can be digested, split, and reviewed as a unit.

| File | `corpus_version` | `family` | Cases |
|---|---|---|---|
| `temporal-update.json` | `memory-temporal-update-corpus-v1` | `temporal-update` | 4 |
| `cascading-invalidation.json` | `memory-cascading-invalidation-corpus-v1` | `cascading-invalidation` | 4 |
| `conflict-and-uncertainty.json` | `memory-conflict-and-uncertainty-corpus-v1` | `conflict-and-uncertainty` | 3 |

All three envelopes carry `schema_version: memory-scenario-v1` and the one
frozen `source_revision` `c08af27`, the commit the observable state is read at.
Every case conforms to the scenario schema unchanged; no case carries a bespoke
field, because the schema's parser drops unknown keys.

### Done-when kinds

Every case tests one kind from the TAS-133 Done-when list. The test pins the
mapping so coverage cannot silently disappear.

| Kind | Meaning |
|---|---|
| `cosmetic-versus-semantic` | A cosmetic edit does not bump the revision; a semantic one does. |
| `changed-definition` | A definition or contract decision changed what a later change may assume. |
| `stale-consumer` | A pinned consumer's revision no longer matches the changed dependency. |
| `reversal` | An outcome was reversed in place and bumped its owning node's revision. |
| `superseded-decision` | An outcome moved to a replacement node and the obsolete node is disposed. |
| `independent-evidence` | A consumer looks stale but a separate decision already supports its conclusion. |
| `unresolved-conflict` | Two current sources conflict and neither clearly controls. |
| `missing-premise` | A required input is absent and one targeted question resolves it. |
| `event-time-differs` | The recorded event time and the real mutation time differ. |

### Invalidation modes

The cascading-invalidation family makes false-positive and false-negative
invalidation separately gradeable:

- **true** — the consumer's conclusion genuinely changes; the direct consumer
  reconciles upstream-to-downstream, and an in-place reversal forces a reread.
- **false-positive** — the mismatch is real but the conclusion already rests on
  a separate, unchanged decision, so the consumer resets the pin and keeps the
  conclusion.
- **false-negative** — the pin still matches numerically because a supersession
  does not change the obsolete node's revision, so the consumer must follow the
  replacement link.

### Correct behaviors

The corpora cover the four corrective behaviors the Done-when names:
`reconcile`, `preserve-alternatives`, `abstain`, and `ask-clarification`. The
competing-rules case uses `action-exact`: the observable state records no
precedence, so the keep-both convention would be defensible, but the gold
memory records a precedence decision that makes the narrower later rule
control; the genuine-conflict case keeps both conclusions and reports the
uncertainty because its only tie-break is blocked.

### Conflict authority

The conflict-and-uncertainty cases ground their resolution norms in the
program's evaluation theory, which states that cascading invalidation must keep
"independently supported conclusions that should survive" and that conflict and
uncertainty may call for preserving alternatives or asking for clarification,
plus the planned uncertainty work in `TAS-127`. The two conflicting sides of
each case are ordinary resolved rules; the resolution norm is the unavailable
memory the case tests.

### Controls and distractors

There are no memory-irrelevant controls in these families: every case needs
unavailable history, so each case's gold evidence cites at least one path
outside `query.observable_paths`, and the test enforces the forbidden-surface
guard. Every case also carries at least one unreferenced **distractor** episode:
related history that no gold evidence cites, so a reader can separate the
minimal memory from surrounding noise.

## 2. Cases

### Temporal update

| Case | Kind | Split | Severity | Cue | Gold memory | Distractor |
|---|---|---|---|---|---|---|
| `temporal-update-cosmetic-edit-001` | cosmetic-versus-semantic | development | minor | Decide whether a matching pin and a reworded sentence force a reread | A reworded contract sentence with an omitted revision bump still forces a reread; a matching pin and a documentation-only label are not proof | A convention that rereads follow only a recorded mismatch |
| `temporal-update-semantic-revision-001` | stale-consumer | development | major | Act after a dependency reports a higher revision | A revision mismatch forces reread, assumption update, and pin reset before executing | One shared pin verdict |
| `temporal-update-event-mutation-time-001` | event-time-differs | held-out | moderate | Refresh a timestamp that is ahead of the host clock | Use the later of the host clock and the previous timestamp; note the clamp | Write-set closure for a public test surface |
| `temporal-update-changed-definition-001` | changed-definition | held-out | major | Preserve an exact version literal to prove byte-identical behavior | One semantic version is declared once and never frozen as an invariant | Vault dot-directory migration |

### Cascading invalidation

| Case | Kind | Invalidation | Split | Severity | Cue | Gold memory | Distractor |
|---|---|---|---|---|---|---|---|
| `cascading-invalidation-transitive-stale-001` | stale-consumer | true | development | major | Reconcile a definition, a consumer, and a downstream node | Reconciliation is consumer-owned and proceeds upstream-to-downstream | One verdict names every pin problem |
| `cascading-invalidation-independent-evidence-001` | independent-evidence | false-positive | development | moderate | Decide whether a consumer's conclusion must change | A separate unchanged decision keeps the conclusion; the pin is still reset | Internal crate-scope reuse |
| `cascading-invalidation-reversal-in-place-001` | reversal | true | held-out | major | Respond to a decision reversed in its owning node | An in-place reversal bumps the revision so a consumer rereads and reverses its assumption | Outcome that moved to a new node |
| `cascading-invalidation-superseded-decision-001` | superseded-decision | false-negative | held-out | major | Act when a matching pin points to a disposed node | Resolution does not change the obsolete revision; follow the replacement link | Reversal in place that did bump its revision |

### Conflict and uncertainty

| Case | Kind | Split | Severity | Cue | Gold memory | Distractor |
|---|---|---|---|---|---|---|
| `conflict-and-uncertainty-competing-rules-001` | unresolved-conflict | development | major | Decide when two current rules collide and no precedence is observable | A recorded precedence decision supplies the missing precedence and makes the narrower later rule control | Cosmetic edit without a revision bump |
| `conflict-and-uncertainty-missing-premise-001` | missing-premise | development | moderate | Resolve which of two migrations a request means | Ask one targeted question instead of guessing or stalling | A semantic revision that needed reconciliation |
| `conflict-and-uncertainty-genuine-conflict-001` | unresolved-conflict | held-out | major | Conclude when a tie-break is blocked | Preserve both conclusions and report the uncertainty | A consumer pin mismatched after a revision |

## 3. Independent review

An independent fresh-context reviewer that did not author the corpus reviewed
every case against the TAS-133 Done-when before the cases were frozen.

### Review record

- **Reviewer:** two independent fresh-context reviews plus a targeted re-check, 2026-09-13.
- **Verdict:** the first two passes blocked on unsourced conflict episodes,
  observable-path leakage, a misattributed false-positive case, an inverted
  event-time case, and a contestable genuine-conflict gold; the re-check
  returned accept-with-minor after the fixes, and the minor items were fixed
  before freeze. Every finding was dispositioned before freeze.

| # | Reviewer finding | Disposition |
|---|---|---|
| 1 | The conflict-and-uncertainty resolution episodes cited nodes that do not state the conflict or clarification rules. | Re-pointed them to `research/agent-memory-theory-evaluation.md` and the planned `TAS-127`, which state the independently-supported-survivor and preserve/abstain/clarify norms, while the two conflicting sides stay on their real rule nodes. |
| 2 | `temporal-update-cosmetic-edit-001` and `cascading-invalidation-transitive-stale-001` observed `graph_check.py`/`index.py`, whose mismatch and dependency-order prose answer the case. | Moved the observables to leak-free surfaces (`revision.py`, `sidecar.py`, `quality_benchmark.py`) and pinned every deciding surface in `_FORBIDDEN_OBSERVABLE`. |
| 3 | `cascading-invalidation-independent-evidence-001` claimed a second authoritative source while citing `DEC-003`, whose point is a single declaration, and its non-bump rule was unsupported. | Re-grounded it on the evaluation theory's independently-supported-survivor rule and an unchanged separate decision, and fixed the citation. |
| 4 | `cascading-invalidation-transitive-stale-001` said the downstream node still matched its pin while the gold called both pins stale. | The query now states the direct consumer bumped its own revision, so both pins genuinely mismatch, and the order is grounded in `TAS-072`/`TAS-077`. |
| 5 | `temporal-update-event-mutation-time-001` described the placeholder as earlier while it is ahead of the host clock, and the gold equated the event and mutation times. | The episode now says the two differ and the gold keeps the later value and notes the clamp; the test asserts the direction and the difference rather than bare substrings. |
| 6 | `conflict-and-uncertainty-stale-source-001` fabricated a vault-location conflict from a status-path evaluation, and the case was solvable from `SKILL.md`. | Dropped the case; its behavior (following a current decision over a historical one) was not required by the Done-when, and the two genuine unresolved-conflict cases remain. |
| 7 | `conflict-and-uncertainty-genuine-conflict-001` cited analyses that actually resolve, so "adopt the more recent" was defensible. | Re-grounded it on the live compactness-versus-progressive-disclosure tension whose only tie-break (`TAS-080`) is blocked, making calibrated preservation the justified action. |
| 8 | `cascading-invalidation-superseded-decision-001` asserted the non-bump without citing the rule. | Cited `references/dependencies.md` and `TAS-009` for "resolution does not change `context_rev`". |
| 9 | Distractor episodes were sometimes misattributed to nodes that record a different change. | Rewrote every unreferenced episode as a rule or generic observation its evidence actually supports, and removed the over-specific incidents. |
| 10 | The prose cue for the cosmetic case read "reconcile after a timestamp move", contradicting the graded outcome. | Corrected the cue to "decide whether a timestamp-only move forces reconciliation". |
| 11 | The review record was an unfilled placeholder while the prose claimed a completed review. | Filled with this record. |
| 12 | Re-check minors: a duplicated guard comment, two omission from the forbidden-surface guard, inconsistent event-time vocabulary, an over-claimed distractor, and an "escalate" action absent from the cited norms. | Deduplicated the comment, added `references/dependencies.md` and `pyproject.toml` to the guard, aligned the event-time wording, reworded the distractor to what `TAS-119` states, and renamed the action to `preserve-both-readings-and-report`. |

## 4. Validation

`tests/test_memory_revision_corpus.py` enforces the three envelopes, schema
conformance of every case, the Done-when kind coverage, the false-positive
versus false-negative invalidation distinction, the reconcile,
preserve-alternatives, abstain, and ask-clarification behavior coverage, the
event-time-versus-mutation-time direction, the forbidden-surface leak guards,
split population, evidence-path existence, arm-neutral tasks, the
declared-action grading, and agreement between this document and all three
corpora.

This test is these three families' guard only. TAS-135 replaces it with the
whole-corpus offline validator, deterministic splits, corpus digest, and
leakage audit that the TAS-121 outcome requires. That audit must also resolve
the inherited contract question the review raised: the evaluation contract
defines currently observable information as repository contents at the frozen
revision, while these families rely on each case's `observable_paths` as the
operative boundary. The per-case boundary is what keeps the cases
memory-required in this corpus.
