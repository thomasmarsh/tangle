---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Record round-trip telemetry and add correctness-gated token cases for each new answer verb.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

The optimization goal is fewer round trips, but the token benchmark records
tokens only. Without a round-trip count, a verb that replaces five shell calls
with one cannot be shown to do so. Each new answer verb also needs its own
exact-value gate so a cheaper answer cannot pass by being wrong.

# Outcome

The token benchmark reports tool-call and shell-invocation counts alongside
tokens when the session stream exposes them, and each direct-answer verb has a
correctness-gated case with a matching baseline.

# Done when

- Round-trip counts are recorded and reported, with a documented fallback when
  the stream does not expose them.
- Each new verb has an exact-value case and a checked-in baseline.
- `make benchmark` stays zero-live and `make test` passes.

# Result

`src/tangle/token_benchmark.py` reports round trips beside tokens. Codex
records each model tool call as a `response_item` whose payload type is a
tool-call kind, and the `exec` tool runs a shell command, so
`_session_round_trips` counts `tool_calls` and `shell_calls`. The record's
`round_trips.samples` keeps one entry per sample (`null` for a stream that
exposes none), `round_trips.median` holds the accepted medians, and
`round_trips.fallback` names the reason
(`session stream exposes no tool-call events`) instead of a fabricated zero; the
`token_benchmark{...}` line gains trailing `tool_calls,shell_calls` columns that
read `n/a,n/a` under that fallback.

`src/tangle/verb_benchmark.py` is a new zero-live gate, `tangle benchmark
verbs`. It generates one small valid vault whose only deliberate defect is a
single stale pin and runs every direct-answer verb against it: `frontier`,
`node TAS-000-foundation`, `impact DEF-010-parser-contract`, `orient`, and
`check --format toon`. Each case compares exact stdout and exit status with the
checked-in baseline `benchmark/verb-baseline.json`; the fixture is validated
structurally with `check --allow-stale` before any case runs, so the expected
`check --format toon` exit `1` is the one intentional mismatch. Absolute node
paths are normalized to `<nodes>`, so the baseline is independent of the
temporary fixture location.

Evidence: `tests/test_token_benchmark.py` covers the tool/shell counts, the
fallback, and both `_emit_record` paths, and drives the round-trip counts through
the fake-Codex record path (`...,true,2,1`); a new
`tests/fixtures/token-usage-tool-calls.jsonl` feeds the count case and the
existing no-tool-call session feeds the fallback case.
`tests/test_verb_benchmark.py` covers `--verify`, baseline-emission equality, and
that a wrong answer fails. `make benchmark` stays zero-live; `make
verb-benchmark`, `make diagnostic-benchmark`, `tangle check nodes`, and
`make test` pass.
