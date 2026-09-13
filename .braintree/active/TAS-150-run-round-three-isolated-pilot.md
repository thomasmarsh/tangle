---
context_rev: 1
priority: P1
updated: 2026-09-13T17:50:54Z
summary: Run the round-three isolated repeat pilot on the repaired corpus and decide the gate.
next: Launch the three 24-child batches, collect the 72-episode result, and decide the gate.
---

Parent [[TAS-147-pilot-corpus-revision]].

# Context

The round-three repair (TAS-147) changed the development queries of the
implicit-retrieval, temporal-update, and poisoning-and-authority cases, so the
corpus, fixture, prompt, and plan digests all changed. This run re-executes the
isolated three-repetition pilot at the repaired revision and decides whether
TAS-147 can resolve and whether TAS-121 can advance. It uses the existing
`scripts/memory_pilot_v2_run.py` runner and the isolated `memory-pilot-child`
profile: one fresh child per episode, no tools, no skills, no inherited
context.

# Outcome

A complete, provenance-preserving 72-episode result decides whether the
repaired corpus separates under the preregistered 2-of-3 paired majority and
the three-or-more stop rule.

# Done when

- The owner authorizes the exact paid run pins and 72-sample bound before execution.
- All 72 samples pass isolation and provenance validation and agree with `memory_scenario.grade`.
- The result records per-repetition grades and case-level majority classifications, then reports `proceed`, `revise`, or `stop` without post-outcome rule changes.
- TAS-147 records the decision and either resolves with TAS-121 advanced or keeps the failing path explicit.
- `braintree check`, `make test`, and `make test-benchmarks` pass.

# Authorization

The owner authorized the bounded live run in session on 2026-09-13, before
execution, after the round-three repair fixed the new pins. Scope: the 12
preregistered development cases, the two pilot arms (`repository-only`,
`oracle`), three paired repetitions each, 72 samples in three deterministic
24-child batches. Pins for the run: protocol `memory-pilot-v2`; corpus digest
`sha256:26c6815ebed88e8f0acea4405b8deb5a389366c89128fb49a961112b835b0f91`;
fixture version `memory-pilot-v2-fixture-1`; source revision `8d15b2ff8938`;
model `deepseek/deepseek-v4-flash` (`deepseek-v4-flash`) at reasoning effort
`high`; prompt revision `memory-pilot-v2-prompt-1`; tool revision `no-tools`;
budget `one isolated child turn per episode; no tools; no retries`; allowed
commands none; grader version `memory-scenario-v1`; plan digest
`sha256:f9a0434bde27f25f1d480ec404da2be6d8f0367bc30359b5c27f0cb0d9625367`.

The plan was generated at source revision `8d15b2ff8938` before this node's
bookkeeping commit, and it is not regenerated afterwards, so the executed plan
digest is exactly the authorized one. The node commit advances `HEAD` without
changing the corpus, the harness, the prompts, or the fixtures; the recorded
run pins therefore name `8d15b2ff8938`, the revision the plan was generated at.

# Execution

The authorization above is complete: do not re-derive it or re-proof it. The
launch is three pi-subagents workflow calls plus one collect, with
`scripts/memory_pilot_v2_run.py` owning fixtures, prompts, and provenance. The
plan and prompts are already generated in `/tmp/mp2`.

Then call the `subagent` tool once per batch file, with `workflowScriptPath`
`/tmp/mp2/batch1.js`, `batch2.js`, and `batch3.js`, each with `cwd` at the repo
root, `context "fresh"`, `skill false`, `async false`, and `timeoutMs
3600000`. Each call fans out 24 isolated `memory-pilot-child` episodes (no
tools, no inherited context, no skills, no fallback) and returns compact
per-child `runId`, `output`, `model`, and `usage`.

```sh
uv run python scripts/memory_pilot_v2_run.py collect /tmp/mp2 \
  --out benchmark/memory-pilot-v2-round3-result.json
```

`collect` scans `$TMPDIR/pi-subagents-uid-*/async-subagent-runs/*/status.json`,
keeps the latest run per planned `workflowKey`, and rebuilds all 72 recorder
samples from `recentOutput`, `modelAttempts[0].usage`, `events.jsonl`, and
`startedAt`/`endedAt`. This run writes a new result file rather than overwriting
the TAS-149 evidence at `benchmark/memory-pilot-v2-result.json`. A missing or
failed sample yields `status: incomplete` and no verdict; rerun only the missing
`workflowKey` and collect again.

# Result

Pending the live run.
