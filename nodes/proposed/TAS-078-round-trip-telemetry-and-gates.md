---
context_rev: 1
priority: P1
updated: 2026-09-12T15:09:27Z
summary: Record round-trip telemetry and add correctness-gated token cases for each new answer verb.
next: Extend benchmark telemetry with tool-call and shell counts and add a correctness-gated case per new verb.
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
