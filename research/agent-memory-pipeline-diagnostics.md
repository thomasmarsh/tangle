# Pipeline diagnostics for the memory causal result

This document is the prose authority for
[`src/tangle/memory_diagnostics.py`](../src/tangle/memory_diagnostics.py)
and the committed
[`benchmark/memory-diagnostics-report.json`](../benchmark/memory-diagnostics-report.json).
It realizes Stage 3, "Diagnose the pipeline", of
[agent-memory-theory-evaluation.md](agent-memory-theory-evaluation.md) and the
diagnostic-label section of
[agent-memory-evaluation-contract.md](agent-memory-evaluation-contract.md).

The module reads the recorded `memory-causal-v1` result and attributes every
failure of the 540-sample five-arm run to exactly one bottleneck. It makes zero
live model calls; `record` writes the report and `verify` re-derives it offline.
The committed report protocol is `memory-diagnostics-v1`.

## Taxonomy

The six labels are the contract's `DIAGNOSTIC_LABELS`. Each belongs to exactly
one pipeline stage and names the later workstream it would justify.

| Label | Stage | Definition | Workstream |
|---|---|---|---|
| `write-miss` | admission | The required memory was never admitted: the arm holds no memory and the required source episodes are unavailable at query time. | corpus admission design; no new memory mechanism |
| `organization-error` | organization | A required source episode was available to write from but the organization or consolidation step omitted it from query-time memory. | TAS-125 episode and consolidation |
| `retrieval-miss` | retrieval | A required source episode was available to write from but bounded retrieval did not surface it within the memory budget. | TAS-124 action-weighted retrieval |
| `stale-or-conflicting-retrieval` | stale-or-conflicting | The delivered memory carried a non-gold decision, action, or failure episode (competing guidance) alongside the gold evidence in a conflict or authority case. | TAS-126 interference and TAS-127 provenance and security |
| `reader-failure` | reading | The required gold evidence was delivered but the action did not follow from it, so the loss is in reading or reasoning. | skill prose and model interaction; not a memory mechanism |
| `action-failure` | action | The required evidence was delivered and the action explicitly discarded or ignored the observation, so the loss is in action selection. | action selection and tooling |

## Adjudication procedure

Retrieval evidence and downstream use are scored separately, so a retrieval
miss can never be reported as a reader or action failure. The ordered rules are:

1. The `oracle` arm is injected with the distilled gold evidence, so its
   retrieval stage is exact by construction and every failure is downstream.
2. The `repository-only` arm holds no memory, so every failure is `write-miss`.
3. For a memory arm, compare the required gold source episodes with the
   query-time memory: `tangle` omitting a source it could write from is
   `organization-error`; `raw-history` or `flat-memory` omitting it is
   `retrieval-miss`.
4. When the required evidence was delivered, a chosen action whose leading verb
   discards or ignores the observation while the expected action does not is
   `action-failure`.
5. Otherwise, a conflict or authority case whose delivered memory also carried a
   non-gold decision, action, or failure is `stale-or-conflicting-retrieval`.
6. Every remaining delivered-evidence failure is `reader-failure`.

Two independent adjudications label the same failures. The committed one is
*evidence-priority* (memory stage first, above). The *behaviour-priority*
reviewer lets an explicit discard/ignore action decide before the memory stage.
Their disagreements are recorded rather than hidden.

## Result

The 540 samples carry 131 incorrect-action failures and no infrastructure or
model-output failures. Admission is the largest stage, but it is entirely the
`repository-only` floor: the corpus is memory-required, which is the intended
result, not a memory-system defect.

| Label | Count | Share | Severity-weighted regret | Arms |
|---|---:|---:|---:|---|
| `write-miss` | 70 | 0.534 | 172 | `repository-only` |
| `organization-error` | 0 | 0.000 | 0 | — |
| `retrieval-miss` | 0 | 0.000 | 0 | — |
| `stale-or-conflicting-retrieval` | 0 | 0.000 | 0 | — |
| `reader-failure` | 40 | 0.305 | 79 | all memory arms and oracle |
| `action-failure` | 21 | 0.160 | 101 | `raw-history`, `flat-memory`, `tangle` |

Retrieval stage, by arm:

| Arm | Failures | Delivered | Missed | Miss rate |
|---|---:|---:|---:|---:|
| `repository-only` | 70 | 0 | 70 | 1.00 |
| `raw-history` | 18 | 18 | 0 | 0.00 |
| `flat-memory` | 23 | 23 | 0 | 0.00 |
| `tangle` | 18 | 18 | 0 | 0.00 |
| `oracle` | 2 | 2 | 0 | 0.00 |

Every memory arm delivered the required gold evidence on every failure it had.
The two-stage split therefore sends 61 of the 131 failures downstream and only
the 70 `repository-only` floor failures to admission.

## Bottlenecks and justified workstreams

- **TAS-127 (uncertainty, provenance, security) — justified.** 20 of the 21
  `action-failure` samples are the `poisoning-and-authority` case, where the
  delivered evidence was discarded rather than adjudicated. That workstream
  already owns source authority and authority-preserving action.
- **TAS-124 (action-weighted retrieval) — not demonstrated.** Every memory arm
  delivered every required source, so no sample is a retrieval miss. The
  retrieval stage is saturated: the shared memory budget (8) is larger than the
  largest case (5 episodes), so `raw-history` and `flat-memory` surface the
  whole construction and cannot miss.
- **TAS-125 (episode and consolidation) — not demonstrated.**
  `organization-error` is zero, and `tangle` is constructed to hold exactly
  the gold chain, so the development run cannot distinguish a correct
  consolidation from an unexercised one.
- **TAS-126 (interference and forgetting) — not demonstrated.** No delivered
  conflict or authority failure carried a non-gold decision, action, or failure
  episode, so `stale-or-conflicting-retrieval` is zero.

The dominant downstream loss (40 `reader-failure` samples) is a reading or
reasoning limit, not a memory mechanism, so it points at skill prose and model
interaction rather than a new retrieval or consolidation feature.

## Independent review

Two fresh-context reviewers that did not author the module audited it before the
report was regenerated: the built-in `reviewer` and an external `codex-exec`
reviewer. Both independently rejected the first draft for the same defect, which
is now the regression test
`tests/test_memory_diagnostics.py::test_flat_memory_and_raw_history_deliver_the_same_episodes`:

- `flat-memory` frames each episode as `note N: <statement>`, so an exact
  statement match scored every `flat-memory` failure as a `retrieval-miss`. The
  corrected match sees through the note prefix, turning those 23 failures from
  retrieval misses into downstream failures and removing the spurious TAS-124
  recommendation.
- The reviewers also showed that the shared memory budget exceeds the largest
  case in the corpus, so the development run cannot demonstrate a retrieval
  miss at all. That limitation is recorded in the report's `limits` block.

Both reviewers also flagged, and the module now records as limits: the
`stale-or-conflicting-retrieval` rule keys on episode kind because the schema
records no explicit supersession link; the `reader-failure` versus
`action-failure` split is a one-action observable, not a proven reading versus
action defect; and the second reviewer is a rule-order sensitivity check, not an
external rater. `verify` establishes deterministic reproduction, not independent
attribution validity.

The committed adjudication is evidence-priority. It agrees with the
behaviour-priority reviewer on 115 of 131 failures (0.8779); the 16 explicit
disagreements are all `repository-only` samples that chose a discard/ignore
action, which the behaviour-priority rule would call `action-failure` and the
committed rule keeps as `write-miss` because no memory was ever delivered.

## Limitations

- The report is development-split (`exploratory`) evidence and decides no claim.
- The frozen corpus still has three non-separating memory-required cases (see
  `TAS-151`); the confirmatory freeze (`TAS-128`) must wait for that repair.
- The retrieval stage is saturated, so the report cannot rank retrieval
  policies; a corpus with more episodes than the memory budget is needed first.
- `stale-or-conflicting-retrieval` and the reader/action boundary need richer
  observables (retrieved-evidence provenance and reasoning traces) before their
  counts can decide a mechanism.

## Reproduction

```sh
uv run tangle benchmark diagnostics record --output benchmark/memory-diagnostics-report.json
uv run tangle benchmark diagnostics verify
uv run pytest -q tests/test_memory_diagnostics.py
```

The report embeds the causal result's corpus digest, plan digest, and source
revision; `verify` re-derives the whole document and rejects both a missing
artifact and a causal result whose corpus digest does not match the committed
corpus.
