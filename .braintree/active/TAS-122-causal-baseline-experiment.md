---
context_rev: 1
priority: P1
updated: 2026-09-13T18:22:25Z
summary: Compare repository-only, raw-history, flat-memory, Braintree, and oracle conditions.
next: Run the authorized separability and five-arm causal batches and collect both results.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-121-evaluation-foundation]] at context_rev 1.

This node owns the shared five-arm causal runner and the residual
`resumption-after-decision-shared-install-001` repair. The repair is folded in
rather than split into its own node because a separating frozen corpus is the
runner's fixture: the repair changes the corpus digest the runner pins, and both
outcomes share one completion boundary (the paid causal run) and one rollback
unit (the corpus revision). TAS-121's recorded residual names a later node, and
this is that later node.

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
