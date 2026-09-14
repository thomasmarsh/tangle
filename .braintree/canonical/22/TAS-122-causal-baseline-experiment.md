---
status: resolved
context_rev: 3
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Compare repository-only, raw-history, flat-memory, Braintree, and oracle conditions.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-121-evaluation-foundation]] at context_rev 1.

This node owns the shared five-arm causal runner and the
`resumption-after-decision-shared-install-001` repair. The repair was folded in
because a separating frozen corpus is the runner's fixture and the repair
changed the corpus digest the runner pins. The round-four separability re-run
found three further non-separating cases, so the corpus-repair outcome is now
tracked independently in [[TAS-151-corpus-separability-repair]]; this node's
own outcome is the measured exploratory comparison.

# Outcome

A matched experiment measures the causal effect of Braintree memory on correct
engineering actions relative to repository-only, raw-history, flat-memory, and
oracle-evidence conditions.

# Done when

- All arms share frozen fixtures, task prompts, tools, model settings, budgets, and graders.
- Accepted samples pass correctness and telemetry gates before entering cost summaries.
- Each selected case and model has the preregistered repetitions or is reported as missing.
- Paired effects, confidence intervals, tokens, turns, tool calls, latency, and failures are committed with exact reproduction commands.
- Exploratory conclusions are not presented as confirmatory evidence.

# Specification

The runner is specified and implemented offline as `braintree benchmark causal`
(`src/braintree/memory_causal.py`), with the prose preregistration in
`research/agent-memory-causal-preregistration.md`, the live fan-out in
`scripts/memory_causal_run.py`, and zero-live tests in
`tests/test_memory_causal.py`. It realizes contract protocol
`memory-causal-v1`:

- **Five arms.** The contract's canonical `repository-only` (floor),
  `raw-history`, `flat-memory`, `braintree` (system under test), and `oracle`
  (ceiling). Every arm shares one task prompt, one set of embedded observable
  bytes, no tools, one model list, one reasoning effort, one statement budget,
  one repetition count, and `memory_scenario.grade`. Only the injected history
  differs: none, ranked public transcript, ranked timestamped notes, the
  dependency-and-decision chain, and the distilled gold evidence respectively.
- **Case set.** The deterministic `memory_corpus.pilot_subset()` development
  cases, spanning all nine families and four curation groups with controls.
- **Power.** Three text models at `high` and three paired repetitions per
  `(case, arm, model)`; 540 planned episodes in nine deterministic batches of
  at most 60 isolated children.
- **Gate.** Correctness-before-cost: only samples that pass the case grader and
  telemetry validation enter cost summaries; latency is recomputed from retained
  timestamps.
- **Analysis.** Paired treatment-minus-baseline effects within `(case, model)`,
  a 95% percentile bootstrap interval over at least 10,000 fixed-seed
  resamples, per-arm tokens, turns, tool calls, latency, and monetary cost, and
  every failure labeled infrastructure, model-output, or incorrect-action.
- **Label.** Development-split evidence is always `exploratory`; incomplete
  runs are `untested` and decide nothing.
- **Reproduction.** `plan`, `dry-run`, and `record` build, validate, and analyze
  the plan without a live call; the result embeds its own commands, plan digest,
  and corpus digest.

`braintree benchmark causal dry-run` builds and validates the plan and
synthetically aggregates a complete development-split result offline.

# Residual repair

`resumption-after-decision-shared-install-001` no longer coincides with the
generic avoid-duplication default: its task now states a locally plausible
packaging guide that points at a per-project copy, while the unavailable history
still records the shared install as deliberate and per-project copies as
rejected. Only the task text changed; the case id, family, split, severity, gold
evidence, allowed actions, and citations are unchanged. The corpus was
re-validated and re-frozen at digest
`sha256:92b6b4d7ec018e458d89c90b965a26d339fbe74732b1fa49e24b2482968d54b1`:
still 53 cases, the same deterministic splits and control balance, and
`benchmark/memory-corpus/manifest.json` regenerated. The historical
`benchmark/memory-pilot-v2-round3-result.json` and the TAS-147 and TAS-150
results keep the prior digest as the record of the run they describe; the causal
plan re-pins the new digest from the frozen corpus. The paid separability
re-run below verifies that the repaired case separates.

# Pilot verification

The authorized separability re-run completed 72/72 on the repaired corpus
(corpus digest
`sha256:92b6b4d7ec018e458d89c90b965a26d339fbe74732b1fa49e24b2482968d54b1`,
plan digest
`sha256:01088e771996eb8584c63f91f79fcaef002740c987bd5fb0325e2dad5dc71124`,
source revision `f39f6201bd3b`) and returned **`stop`**. The repaired
`resumption-after-decision-shared-install-001` now separates: repository-only
correct 1/3, oracle 3/3. Three memory-required cases fail the preregistered
2-of-3 paired majority and meet the three-or-more stop rule:

- `admission-retain-label-stability-hypothesis-001`: repository-only correct
  2/3, 1 separation.
- `forgetting-and-interference-irrelevant-growth-001`: repository-only correct
  2/3, 1 separation.
- `poisoning-and-authority-direct-injection-001`: oracle correct 1/3, 0
  separations; the oracle follows the task's quarantine-whole convention
  instead of the gold distinction on two repetitions.

All three controls stay valid. Per-repetition grades and telemetry are in
`benchmark/memory-pilot-v2-round4-result.json`. The `stop` verdict means the
corpus is not yet ready for the confirmatory evaluation and needs another
repair pass; it is recorded as a residual rather than hidden. The five-arm
causal run below is exploratory and remains valid evidence about arm behavior
even while those corpus cases are non-separating.

# Authorization

The owner granted a standing authorization in session on 2026-09-13 covering
all paid runs in this evaluation program, explicitly ending per-run
authorization requests; this node executes under that standing grant.

The plans were generated at revision `f39f6201bd3b` before this authorization
commit. The plan digest content-addresses its source-revision pin, so the
recorded plans name `f39f6201bd3b` and are run without regeneration; the corpus,
harness, prompts, and fixtures are unchanged by this bookkeeping commit.

- Corpus digest
  `sha256:92b6b4d7ec018e458d89c90b965a26d339fbe74732b1fa49e24b2482968d54b1`.
- Separability pilot: protocol `memory-pilot-v2`, plan digest
  `sha256:01088e771996eb8584c63f91f79fcaef002740c987bd5fb0325e2dad5dc71124`,
  72 samples (12 cases × 2 arms × 3 repetitions), `deepseek/deepseek-v4-flash`
  at `high`.
- Five-arm causal run: protocol `memory-causal-v1`, plan digest
  `sha256:abd5c4437fa74638cfd411281c92fde167074e6650d9fb2682efced2cacfc677`,
  540 samples (12 cases × 5 arms × 3 models × 3 repetitions), three models at
  `high`.

# Result

The five-arm causal run was re-executed after the separability repair that
[[TAS-152-conflict-separability-residual]] owns, because that repair changed the
runner's fixture. It completed 540/540 with evidence `exploratory` (development
split) and decision `exploratory`. Pins: corpus digest
`sha256:06e7a09963e484b1d38eb4ea6ed6d3da5fc8790183e6e0b5e96e3e1037c07ce5`,
plan digest
`sha256:636c25705154e95bdd976b24233c0ae88927096091d3ec91e8b8c05603e3aac2`,
source revision `20c88e7ba1ed`, three models at `high`. All 540 samples pass
isolation, model, prompt, and telemetry validation; none is incomplete.

Paired effects (95% percentile bootstrap, 10,000 fixed-seed resamples over
`(case, model)` strata, 108 pairs and 36 strata per contrast):

- `braintree - repository-only`: **+0.333**, CI [0.167, 0.463] — excludes zero.
- `braintree - raw-history`: **-0.046**, CI [-0.176, 0.046] — includes zero.
- `braintree - flat-memory`: 0.000, CI [-0.111, 0.083] — includes zero.
- `oracle - braintree`: +0.389, CI [0.213, 0.528] — excludes zero, leaving
  measurable headroom below the ceiling.

The contract's support criterion requires improvement against both
repository-only and raw-history; the raw-history interval includes zero, so the
claim is **not** supported on this development run. The result is labelled
`exploratory`, not confirmatory, as preregistered. The re-run reproduces the
prior qualitative conclusion on the fully separating corpus.

Costs over correctness-gated samples:

| Arm | admitted | total tokens | output tokens | model turns | latency ms | cost |
|---|---|---|---|---|---|---|
| repository-only | 28 | 11,442 | 7,564 | 28 | 84,469 | $0.0172 |
| raw-history | 69 | 72,246 | 45,909 | 69 | 341,319 | $0.1069 |
| flat-memory | 64 | 68,854 | 42,555 | 65 | 436,213 | $0.1356 |
| braintree | 64 | 45,307 | 36,097 | 64 | 315,101 | $0.0964 |
| oracle | 106 | 40,591 | 24,772 | 106 | 284,614 | $0.0551 |

Braintree admits 64 correct samples against raw-history's 69 at a lower total
token count (45,307 versus 72,246) and comparable monetary cost. Of 540 samples,
209 are incorrect-action failures; none are infrastructure or model-output
failures. Per-case and per-model arms, per-sample telemetry, and failure labels
are in `benchmark/memory-causal-result.json`, whose embedded reproduction
commands pin both digests.

Residual: the round-five separability pilot returned **`revise`**, which
[[TAS-152-conflict-separability-residual]] resolved; its round-seven re-run
returned **`proceed`** with every memory-required case separating, so this node's
replacement causal result is the final development-split evidence before the
confirmatory freeze.
