# Whole-corpus validation, splits, and digest

This document is the prose authority for the whole gold memory corpus. The
machine-readable halves are [`src/braintree/memory_corpus.py`](../src/braintree/memory_corpus.py),
the nine family envelopes under [`benchmark/memory-corpus/`](../benchmark/memory-corpus),
and the committed [`manifest.json`](../benchmark/memory-corpus/manifest.json).
The case format belongs to
[`src/braintree/memory_scenario.py`](../src/braintree/memory_scenario.py) and
[`research/agent-memory-scenario-schema.md`](agent-memory-scenario-schema.md);
the evaluation protocol belongs to
[`research/agent-memory-evaluation-contract.md`](agent-memory-evaluation-contract.md).
This document must not restate either literal set.

TAS-131 through TAS-134 curated the nine families. TAS-135 owns the whole-corpus
validator, the deterministic development/held-out split, the corpus digest and
verify mode, and the leakage audit; it reconciles the two inherited questions
about the observable boundary and the per-family control balance. Everything
here is offline and makes **zero live model calls**, and `braintree benchmark
corpus verify` imports no optional model runtime.

## 1. Corpus layout

One envelope per family, keyed by the family name. Protocol: `memory-corpus-v1`.
The corpus is 53 cases,
inside the contract's 40–60 admitted range. Each envelope carries its own
`corpus_version` and one frozen `source_revision`.

| File | Cases | Source revision | Development | Held-out |
|---|---|---|---|---|
| `admission.json` | 15 | `86d81e3` | 9 | 6 |
| `resumption.json` | 7 | `b8cd7d5` | 4 | 3 |
| `implicit-retrieval.json` | 8 | `b8cd7d5` | 4 | 4 |
| `temporal-update.json` | 4 | `c08af27` | 2 | 2 |
| `cascading-invalidation.json` | 4 | `c08af27` | 2 | 2 |
| `conflict-and-uncertainty.json` | 3 | `c08af27` | 2 | 1 |
| `experience-transfer.json` | 4 | `f91f3be` | 2 | 2 |
| `forgetting-and-interference.json` | 4 | `f91f3be` | 2 | 2 |
| `poisoning-and-authority.json` | 4 | `f91f3be` | 2 | 2 |

The whole corpus is 29 development and 24 held-out cases. `manifest.json` holds
the per-family digests, the frozen split assignment, the control balance, and
the whole-corpus digest; the validator re-derives it and fails on any drift.

## 2. Validation

`memory_corpus.validate()` covers every invariant the TAS-135 Done-when names.
The scenario schema already enforces case identity, family, split, severity,
source revision, episode order, gold evidence sources, graders, allowed and
acceptable actions, and repository-relative paths; the whole-corpus validator
adds the envelope and cross-case checks:

- every family has exactly one envelope, named `<family>.json`, with the
  admitted `corpus_version`, the current `schema_version`, and a well-formed
  `source_revision`;
- every case's family and source revision agree with its envelope;
- case ids are unique across the whole corpus, not only inside a family;
- every cited evidence or observable path resolves in the repository;
- each family meets the three-case diagnostic minimum and the corpus stays
  inside the 40–60 admitted range;
- each family and each curation group contributes to both splits and each
  family's split is balanced within a third;
- every outcome stratum with two or more cases is balanced within a third;
- no source incident's variants cross a split;
- the corpus carries memory-irrelevant controls in more than one family;
- the forgetting family covers all three interference growth classes; and
- every conflict-and-uncertainty case cites the evaluation theory authority.

`memory_corpus.leakage()` audits the intended-arm boundary: a node id, wikilink,
expected outcome, or allowed action in the shared task prompt; a gold statement
copied into the task; a gold statement that merely restates a construction
episode; and the expected action or a distinctive gold phrase written into a
file the query exposes.

## 3. Information boundary

The contract's frozen source revision is the **outer envelope**: every path a
case cites must exist at that revision. The **operative boundary** is the
case's `query.observable_paths`, the subset of the revision the arm is given. A
case is a **memory-irrelevant control** when its gold evidence cites only
observable paths, and **memory-required** otherwise. This is the per-case
boundary the curated families already used, now applied corpus-wide; it is what
keeps a case memory-required even when the repository as a whole records the
deciding history somewhere.

A `.braintree/<status>/<name>.md` citation resolves by node **name** across
every status directory, because a node legitimately moves between directories
and its stable identity is its name. The literal directory is retained in the
case to record where the node sat when the case was curated.

## 4. Deterministic splits

The split is frozen in each case and re-derived into `manifest.json`; no
randomness is involved, so the manifest is byte-identical on every run.

- **Incident grouping.** `source_incident` strips a trailing sequence number, so
  `-001` and `-002` are variants of one source incident. All variants must sit
  in one split; the validator fails when an incident crosses the boundary.
- **Family and group stratification.** Every family and every curation group
  contributes at least one case to each split, and no family's split is more
  lopsided than two-to-one.
- **Outcome stratification.** Cases are balanced within an outcome stratum. The
  admission family's stratum is its leading action verb (`retain`,
  `update-existing`, `discard`); every other family's accepted action is fine
  enough to be its own stratum.

## 5. Control balance decision

The contract asks the corpus for memory-irrelevant controls so a system cannot
score by always consulting memory. The validator enforces that requirement at
the **corpus** level: controls appear in more than one family. The per-family
balance is recorded in the manifest and in the families' own prose authorities:

| Family | Observable-only controls | Memory-required |
|---|---|---|
| `admission` | 8 | 7 |
| `resumption` | 1 | 6 |
| `implicit-retrieval` | 2 | 6 |
| `temporal-update` | 0 | 4 |
| `cascading-invalidation` | 0 | 4 |
| `conflict-and-uncertainty` | 0 | 3 |
| `experience-transfer` | 0 | 4 |
| `forgetting-and-interference` | 0 | 4 |
| `poisoning-and-authority` | 0 | 4 |

The revision-and-conflict and transfer-interference-and-authority groups are
deliberately all memory-required: every case there tests a memory-dependent
action or a memory-hostile outcome, and adding an observable-only control would
dilute the family. This is the reviewed exception recorded in the TAS-133 and
TAS-134 review records; the contract prose was reconciled to the corpus-level
rule. The two groups still constrain an always-consult strategy, because the
transfer, interference, and authority cases punish blindly following stored
content.

## 6. Growth-size scaling decision

The forgetting-and-interference family freezes the three interference growth
**classes** (`irrelevant-growth`, `superseded-growth`, `near-duplicate-growth`)
and the validator fails when one disappears. Growth **size** is a harness knob,
not corpus content: the schema records no size field, and the causal runner and
the interference experiment own the sizes they instantiate. This document owns
the decision that the class is frozen here and the size is out of corpus scope.

## 7. Conflict-norm citation

The conflict-and-uncertainty cases ground their resolution norms in
[`research/agent-memory-theory-evaluation.md`](agent-memory-theory-evaluation.md)
and in the resolved
[`TAS-127-uncertainty-provenance-security`](../.braintree/resolved/TAS-127-uncertainty-provenance-security.md).
The validator requires the theory citation; the node is recorded here as the
dependency that owns the uncertainty policy, so a later change to that policy
knows it may affect these norms. TAS-127's own authority case set lives
separately in
[`benchmark/memory-authority-cases.json`](../benchmark/memory-authority-cases.json)
and never edits this corpus, so the digest is unchanged by that work.

## 8. Digest and verify mode

`memory_corpus.corpus_digest()` content-addresses the canonical corpus: each
case is normalized through the schema, families are ordered by name, and the
whole record is serialized with sorted keys and stable separators before
hashing. `family_digest()` does the same for one family. `build_manifest()`
collects the digests, counts, splits, control balance, and audit notes; `verify()`
re-derives and compares them; `freeze()` rewrites `manifest.json` after a clean
validation.

```sh
braintree benchmark corpus verify   # re-derive and compare; exit 1 on drift
braintree benchmark corpus freeze   # re-validate and rewrite the manifest
```

## 9. Residuals

- Growth sizes are owned by the causal runner and the interference experiment,
  which instantiate the frozen classes.
- The conflict norms cite the resolved
  [`TAS-127-uncertainty-provenance-security`](../.braintree/resolved/TAS-127-uncertainty-provenance-security.md);
  that node's authority case set and rate measurement did not change the corpus
  digest or any conflict norm.
- `research/agent-memory-evaluation-contract.md` was reconciled to the
  corpus-level control rule and the per-case operative boundary; the change
  bumped TAS-129 to `context_rev 2` and TAS-130 was re-pinned.
