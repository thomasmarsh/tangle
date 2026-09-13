---
context_rev: 1
priority: P1
updated: 2026-09-13T17:19:01Z
summary: Preregister and implement an isolated three-repetition Pi pilot harness.
---

Parent [[TAS-147-pilot-corpus-revision]].

# Context

The prior pilot used the built-in Pi `delegate` child, whose inherited project
context exposed `AGENTS.md` outside the arm fixture. Its result also used
`deepseek/deepseek-v4-pro` instead of the intended
`deepseek/deepseek-v4-flash`, omitted comparison pins required by the evaluation
contract, and did not preserve run ids or repetition indexes in the current
artifact. Repeating that procedure would not produce comparable evidence.

The replacement protocol uses three fresh-context repetitions of every
`(case, arm)` pair. A memory-required case separates only when at least two of
its three paired repetitions have repository-only incorrect and oracle correct;
a control is valid when repository-only is correct in at least two of three
repetitions. The existing `proceed`/`revise`/`stop` thresholds then apply to the
case-level results. Infrastructure failures produce an incomplete run rather
than being graded as model failures.

# Outcome

A zero-live, repository-owned pilot-v2 harness can reproducibly build each arm
fixture, launch isolated Pi subagents, retain complete sample provenance, and
aggregate the preregistered majority decision without exposing repository or
operator context to a child.

# Done when

- A dedicated project child profile uses a replacement system prompt, fresh context, no tools, no skills, no project or global context, and no ambient extensions.
- The child model is explicitly `deepseek/deepseek-v4-flash` at `high` effort with no fallback model.
- The exact prompt template, arm-fixture builder, paired-majority rule, incomplete-run behavior, and output parser are committed and covered by zero-live tests.
- The run plan contains 72 uniquely keyed episodes and can be split into three 24-child Pi workflow batches below the 64-child per-run limit.
- Every contract pin, repetition index, Pi child run id, raw output reference, grade, token/cost telemetry, and correctly computed latency is retained.
- A clean-checkout dry run validates fixtures, keys, prompt digests, aggregation, and result-schema completeness without making a live model call.
- `braintree check` and `make test` pass.

# Result

Implemented the zero-live isolated pilot-v2 harness.

- Added `src/braintree/memory_pilot.py`: protocol constants, an arm-fixture
  builder that embeds every observable file and the arm's memory, a
  deterministic 72-episode plan (12 cases x 2 arms x 3 repetitions) in three
  24-child batches, a strict output parser, a provenance and telemetry recorder
  with latency computed from retained timestamps, and the paired-majority
  `proceed`/`revise`/`stop` verdict with incomplete-run handling.
- Added the project child profile `.pi/agents/memory-pilot-child.md`:
  replacement system prompt, fresh context, no tools, no skills, no project or
  global context, no ambient extensions, and `deepseek/deepseek-v4-flash` at
  `high` effort with no fallback model.
- Added `research/agent-memory-pilot-v2-preregistration.md` and
  `tests/test_memory_pilot_v2.py` (27 zero-live tests), and wired
  `braintree benchmark pilot plan|dry-run|record` into the CLI.
- `braintree benchmark pilot dry-run` passes: 72 unique episodes in three
  24-child batches, pins covering every contract field, a synthetic complete run
  that aggregates to `proceed`, and a valid result schema, with no live call.
- `braintree check` passed with 179 nodes; `make test` passed with 567 tests and
  3 expected skips.
