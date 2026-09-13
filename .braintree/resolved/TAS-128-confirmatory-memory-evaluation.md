---
context_rev: 1
priority: P1
updated: 2026-09-13T21:31:56Z
summary: Run the frozen confirmatory evaluation and settle the supported memory contract.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-127-uncertainty-provenance-security]] at context_rev 1.

# Outcome

A held-out confirmatory run determines which claims and mechanisms belong in the Braintree contract and documents the remaining limits.

# Done when

- Selected mechanisms, prompts, models, budgets, graders, and analysis are frozen before held-out execution.
- Paired results include uncertainty intervals, missing samples, and correctness-cost Pareto comparisons.
- The report distinguishes confirmed, rejected, exploratory, and untested claims.
- Accepted contract changes, benchmark baselines, documentation, and reversal criteria are committed and all required suites pass.

# Authorization

The owner's standing authorization of 2026-09-13 covers all paid runs in this
evaluation program, including this confirmatory run. The exact plan was frozen
at revision `ee7c25d9bc28` before execution and is recorded here:

- protocol `memory-causal-confirmatory-v1`; split `held-out`; corpus digest
  `sha256:06e7a09963e484b1d38eb4ea6ed6d3da5fc8790183e6e0b5e96e3e1037c07ce5`.
- plan digest
  `sha256:4228b2b9f26e25d17726d6508832b123ffb3da5420727ea7da29eac9d5ecac39`.
- fixture `memory-causal-fixture-1`; prompt `memory-causal-prompt-1`; tools
  `no-tools`; grader `memory-scenario-v1`; reasoning effort `high`.
- models `deepseek/deepseek-flash`, `deepseek/deepseek-v4-flash`, and
  `deepseek/deepseek-v4-pro`; budget one isolated child turn per episode, no
  retries; 1,080 samples (24 cases x 5 arms x 3 models x 3 repetitions) in 18
  batches of at most 60 children.

The plan is generated at `ee7c25d9bc28` and is not regenerated, so the executed
plan digest is exactly the authorized one; this node's bookkeeping commit does
not change the corpus, harness, prompts, or fixtures.

# Freeze

The selected mechanisms and the confirmatory protocol are frozen in
`research/agent-memory-confirmatory-preregistration.md`. The run tests the
contract's single claim with the five canonical arms on the whole frozen
held-out split: 24 cases (19 memory-required and 5 controls) across all nine
families and all four curation groups. Per the program's mechanism decisions,
no new retrieval, consolidation, interference, or sparse-provenance mechanism
is under test; the `braintree` arm represents the existing graph lifecycle,
revision pins, bounded retrieval, and existing Markdown and Git evidence.

The zero-live gate passes: `braintree benchmark causal plan --split held-out`
and `braintree benchmark causal dry-run --split held-out` build, validate, and
synthetically aggregate the plan to `complete` / `confirmatory` / `confirmed`
without a model call. The development plan keeps protocol `memory-causal-v1`
and its 540-episode geometry, and `make test` (646 passed, 3 skipped) and
`make test-benchmarks` (79 passed) pass.

# Execution

The freeze is complete. The held-out run launches 18 deterministic batches with
`scripts/memory_causal_run.py generate /tmp/memory-causal-confirmatory --split
held-out`, one `subagent` workflow call per batch, then `collect` to
`benchmark/memory-causal-confirmatory-result.json`. A missing or failed sample
leaves the run `incomplete` and `untested`; only a complete run decides the
claim. On completion, record the accepted or rejected contract change, its
reversal criterion, and the updated benchmark baselines here.

# Result

The frozen held-out confirmatory run is complete and rejects the contract
claim. `benchmark/memory-causal-confirmatory-result.json` records 1,080/1,080
samples (24 held-out cases x 5 arms x 3 models x 3 repetitions) with zero
missing or infrastructure failures, evidence `confirmatory`, decision
`rejected`.

- `braintree` - `repository-only`: +0.093, 95% CI [0.037, 0.148] — excludes
  zero.
- `braintree` - `raw-history`: -0.023, 95% CI [-0.065, 0.000] — includes
  zero, so the contract's support criterion fails.
- `oracle` - `braintree`: +0.028, 95% CI [-0.009, 0.069] — braintree is
  statistically indistinguishable from the ceiling.

The loss is one held-out case, `admission-update-existing-seam-reuse-001`
(braintree 1/3 models, raw-history 3/3, repository-only 0/3). No mechanism is
adopted and the existing Markdown and Git evidence contract stands; the
reversal criterion and claim dispositions are in
`research/agent-memory-confirmatory-report.md`. The run executed at a
launch-time throttle of five concurrent isolated children per batch; the
frozen plan and digest are unchanged. `braintree check`, `make test` (646
passed, 3 skipped), and `make test-benchmarks` (79 passed) pass.
