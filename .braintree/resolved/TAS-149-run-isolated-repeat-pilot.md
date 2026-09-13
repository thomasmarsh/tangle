---
context_rev: 1
priority: P1
updated: 2026-09-13T17:36:09Z
summary: Run the isolated three-repetition Pi separability pilot and decide the gate.
---

Parent [[TAS-147-pilot-corpus-revision]].

# Context

Depends on [[TAS-148-isolated-repeat-pilot-harness]] at context_rev 1.

The live run uses the frozen development subset and corpus digest, two arms,
three paired repetitions, one fresh isolated Pi child per episode, and
`deepseek/deepseek-v4-flash` at `high` effort. It does not reuse the prior Pro
samples. Execute the three deterministic 24-child batches from one clean source
revision, stopping without a verdict if a required sample or contract pin is
missing.

# Outcome

A complete, provenance-preserving 72-episode result decides whether TAS-147 can
resolve and whether TAS-121 can advance under the preregistered case-level
majority and phase-one rules.

# Done when

- The owner authorizes the exact paid run pins and 72-sample bound before execution.
- All samples pass isolation and provenance validation and agree with `memory_scenario.grade`.
- The result records per-repetition grades and case-level majority classifications, then reports `proceed`, `revise`, or `stop` without post-outcome rule changes.
- TAS-147 records the decision and either resolves with TAS-121 advanced or keeps the failing path explicit.
- `braintree check`, `make test`, and `make test-benchmarks` pass.

# Authorization

The owner explicitly authorized the bounded live run in session on
2026-09-13, before execution, after confirming the exact pins and bound.
Scope: the 12 preregistered development cases, the two pilot arms
(`repository-only`, `oracle`), three paired repetitions each, 72 samples in
three deterministic 24-child batches. Pins for the run: protocol
`memory-pilot-v2`; corpus digest
`sha256:0e294c4e3a61edfb72288ad1bb936f287500c7d080e481163d0bf5fe8e647a24`;
fixture version `memory-pilot-v2-fixture-1`; model
`deepseek/deepseek-v4-flash` (`deepseek-v4-flash`) at reasoning effort
`high`; prompt revision `memory-pilot-v2-prompt-1`; tool revision `no-tools`;
budget `one isolated child turn per episode; no tools; no retries`;
allowed commands none; grader version `memory-scenario-v1`; plan digest
`sha256:167639b3dfe5e79fb92c6c645c5595e5cd922e1dbcdd5961197ebc0b787b13c3`.
Each episode runs as the isolated `memory-pilot-child` profile with only its
arm fixture embedded in the prompt. The source revision is the clean checkout
revision `generate` records in the run pins; the harness was confirmed at
`bfab3f03a359` and later bookkeeping commits do not change harness behavior.

# Execution

The authorization above is complete: do not re-derive it or re-proof it. The
launch is three pi-subagents workflow calls plus one collect, with
`scripts/memory_pilot_v2_run.py` owning fixtures, prompts, and provenance:

```sh
uv run python scripts/memory_pilot_v2_run.py generate /tmp/mp2
```

Then call the `subagent` tool once per batch file, with
`workflowScriptPath` `/tmp/mp2/batch1.js`, `batch2.js`, and `batch3.js`, each
with `cwd` at the repo root, `context "fresh"`, `skill false`,
`async false`, and `timeoutMs 3600000`. Each call fans out 24 isolated
`memory-pilot-child` episodes (no tools, no inherited context, no skills, no
fallback) and returns compact per-child `runId`, `output`, `model`, and
`usage`.

```sh
uv run python scripts/memory_pilot_v2_run.py collect /tmp/mp2 \
  --out benchmark/memory-pilot-v2-result.json
```

`collect` scans `$TMPDIR/pi-subagents-uid-*/async-subagent-runs/*/status.json`,
keeps the latest run per planned `workflowKey`, and rebuilds all 72 recorder
samples from `recentOutput`, `modelAttempts[0].usage`, `events.jsonl`, and
`startedAt`/`endedAt`, so workflow Returns never need transcription. One probe
episode already ran during harness verification and is deduped by latest run.
A missing or failed sample yields `status: incomplete` and no verdict; rerun
only the missing `workflowKey` and collect again.

# Result

The authorized 72-episode pilot is **complete** with the preregistered verdict
**`stop`**.

Pins recorded by the run: protocol `memory-pilot-v2`; corpus digest
`sha256:0e294c4e3a61edfb72288ad1bb936f287500c7d080e481163d0bf5fe8e647a24`;
fixture `memory-pilot-v2-fixture-1`; source revision `472b090b90aa`; model
`deepseek/deepseek-v4-flash` (`deepseek-v4-flash`) at `high`; prompt
`memory-pilot-v2-prompt-1`; tools `no-tools`; budget one isolated turn, no
retries; grader `memory-scenario-v1`; plan digest
`sha256:b791616f8fd040d2a050361078c36a487ba938eb99e5e7dfa033eb69b089292f`. That
plan digest differs from the authorization's `sha256:167639b3...` only because
it content-addresses the derived `source-revision` pin, which advanced from the
harness revision `bfab3f03a359` to the clean checkout `472b090b90aa`; all other
pins and all 72 episode identities are byte-identical, and the owner
authorized executing at the current revision in session.

Three deterministic 24-child batches fanned out the 72 isolated
`memory-pilot-child` episodes (fresh context, no tools, no skills, no inherited
context), and `scripts/memory_pilot_v2_run.py collect` rebuilt every sample from
retained async run state (54/72 after the batches). A launch-time pi-subagents
completion-guard false positive rejected all six arm/repetition samples of three
read-only cases
(`admission-discard-cache-speculation-001`,
`implicit-retrieval-control-version-declaration-001`,
`experience-transfer-recurring-failure-001`) because the fully embedded episode
prompt tripped its implementation heuristic while the profile intentionally
declares no tools. The owner directed the harness fix: `completionGuard: false`
on `.pi/agents/memory-pilot-child.md`, which adds no tools and preserves
isolation. Re-running exactly those 18 missing `workflowKey`s and collecting
again returned 72/72 complete.

Case-level 2-of-3 paired majority (repository-only correctness by repetition;
oracle correct 3/3 on all 12 cases):

- separates: `admission-retain-label-stability-hypothesis-001` (0/3 repo),
  `resumption-after-decision-shared-install-001` (1/3),
  `cascading-invalidation-independent-evidence-001` (0/3),
  `conflict-and-uncertainty-competing-rules-001` (1/3),
  `experience-transfer-recurring-failure-001` (0/3),
  `forgetting-and-interference-irrelevant-growth-001` (1/3)
- fails: `implicit-retrieval-after-decision-derived-membership-001` (3/3 repo),
  `temporal-update-cosmetic-edit-001` (2/3 repo),
  `poisoning-and-authority-direct-injection-001` (3/3 repo)
- controls valid 3/3 repository-only: `admission-discard-cache-speculation-001`,
  `resumption-control-vault-rename-001`,
  `implicit-retrieval-control-version-declaration-001`

Three memory-required cases fail to separate, meeting the preregistered
three-or-more rule, so the verdict is `stop` with no post-outcome rule change.
All samples pass isolation and provenance validation and agree with
`memory_scenario.grade`. Per-repetition grades and telemetry are recorded in
`benchmark/memory-pilot-v2-result.json`. TAS-147 keeps the failing path
explicit and is not resolved.
