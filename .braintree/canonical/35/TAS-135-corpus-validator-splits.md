---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Validate, balance, split, and digest the gold memory-evaluation corpus.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-129-benchmark-claim-contract]] at context_rev 2.
Depends on [[TAS-131-admission-scenarios]] at context_rev 1.
Depends on [[TAS-132-resumption-retrieval-scenarios]] at context_rev 1.
Depends on [[TAS-133-revision-conflict-scenarios]] at context_rev 1.
Depends on [[TAS-134-transfer-interference-authority-scenarios]] at context_rev 1.

Residual handed off from [[TAS-133-revision-conflict-scenarios]] and
[[TAS-134-transfer-interference-authority-scenarios]]: the evaluation contract
defines observable information as repository contents at the frozen revision,
while the curated families use each case's `observable_paths` as the operative
boundary. The whole-corpus leakage audit must reconcile that boundary, note that
the conflict norms cite `research/agent-memory-theory-evaluation.md` plus the
still-proposed [[TAS-127-uncertainty-provenance-security]], own the per-family
memory-irrelevant control balance the contract asks for, and own any growth-size
scaling.

# Outcome

An offline validator proves the corpus is structurally valid, balanced enough for diagnosis, free of obvious answer leakage, reproducibly split, and content-addressed before experiments select mechanisms.

# Done when

- Validation covers schema, unique IDs, source revisions, paths, episode order, gold evidence, graders, family labels, and case counts.
- Development and held-out splits are deterministic, stratified by family and outcome, and prevent variants of one source incident from crossing splits.
- Leakage checks flag node IDs, gold phrases, or answers exposed outside the intended arm.
- The committed corpus carries a digest and verify mode that imports no optional model runtime.
- Tests include one valid corpus and focused failures for every invariant.

# Result

`src/braintree/memory_corpus.py` is the whole-corpus validator, deterministic
splitter, leakage auditor, and content-addresser, and
`research/agent-memory-corpus-validation.md` is its prose authority. The
committed `benchmark/memory-corpus/manifest.json` freezes the per-family
digests, the 53-case count, the development/held-out assignment, the control
balance, the growth classes, the audit notes, and the whole-corpus digest
`sha256:8caf44eae2a841e4ff4e2ad4f11ee85bfa87cbca048065539a94f18f65ed7d02`.

- Validation covers every named invariant. The schema owns case identity,
  family, split, severity, episode order, gold-evidence sources, graders, and
  repository-relative paths; the validator adds envelope identity and version,
  globally unique case ids, envelope/case source-revision agreement, physical
  path existence, the three-case family minimum and 40–60 corpus range, split
  and outcome stratification, incident grouping, control and growth balance, and
  the conflict-norm citation.
- Splits are deterministic because each case carries its split and the manifest
  re-derives it with no randomness. Every family and curation group contributes
  to both splits, no family is more lopsided than two-to-one, every outcome
  stratum of two or more cases is balanced within a third, and
  `source_incident` groups trailing-sequence variants so no incident crosses the
  boundary.
- Leakage flags a node id, wikilink, expected outcome, or allowed action in the
  shared task prompt; a gold statement copied into the task; gold evidence that
  restates a construction episode; and the expected action or a distinctive
  gold phrase written into a file the query exposes.
- The manifest is content-addressed and re-derived by
  `braintree benchmark corpus verify` (`freeze` rewrites it). The validator
  imports no optional model runtime and the whole corpus makes zero live calls.
- `tests/test_memory_corpus.py` (49 tests) proves the committed corpus and
  manifest valid and mutates one invariant at a time to pin every failure mode.
  The four per-family guards remain as focused subset checks; their cited-path
  guards now call `memory_corpus.path_exists`, which resolves a
  `.braintree/<status>/<name>.md` citation by node name across status
  directories so a legitimate node move cannot break a corpus citation.

The two inherited questions are reconciled:

- **Observable boundary.** The frozen source revision is the outer envelope:
  every cited path must exist there. The operative per-case boundary is
  `query.observable_paths`; a case is a memory-irrelevant control when its gold
  cites only observable paths and memory-required otherwise. This was already
  the curated families' rule, now applied corpus-wide.
- **Control balance and growth size.** The validator enforces the contract's
  purpose at the corpus level: controls in more than one family (admission 8,
  resumption 1, implicit-retrieval 2). The revision-and-conflict and
  transfer-interference-and-authority groups are all memory-required by design
  and recorded as the reviewed exception from TAS-133/TAS-134. The forgetting
  family freezes the three growth classes; the growth *size* is a harness knob
  owned by the causal runner and interference experiment.
  `research/agent-memory-evaluation-contract.md` was reconciled to the
  corpus-level control rule and the per-case boundary, which bumped
  [[TAS-129-benchmark-claim-contract]] to `context_rev 2`; its pinned consumer
  [[TAS-130-scenario-schema-grader]] was re-pinned to `context_rev 2` in the
  same change.

Evidence: `tests/test_memory_corpus.py` (49 tests). `make test` passes (528
passed, 3 skipped, 79 deselected); `make test-benchmarks` passes (79 passed),
with the token fixture file count reconciled to 83 now that three modules
(`memory_contract`, `memory_scenario`, `memory_corpus`) join the installed
skill tree; `ruff check`, `mypy`, and `braintree benchmark corpus verify` pass;
the corpus and its tests make zero live model calls.
