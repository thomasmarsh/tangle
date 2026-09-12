---
context_rev: 1
priority: P2
updated: 2026-09-12T15:09:27Z
summary: Run the staged token and round-trip A/B comparing the pre-thrust state with the landed direct-answer surface.
next: Record matched correctness-gated A/B samples of the pre-thrust and landed states.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

This runs only after the direct-answer surface and the telemetry land. It
compares the current state at the start of this thrust with the landed state on
the same fixtures, prompt, model, effort, and CLI version, and decides keep,
revise, or revert for each change.

# Outcome

Matched correctness-gated samples for the pre-thrust and landed states, with
per-change token and round-trip deltas and an explicit keep, revise, or revert
decision.

# Done when

- Pre-thrust and landed samples share their fixture, prompt, model, effort, and
  CLI version.
- Every sample passes its exact-value gate.
- The report records token and round-trip deltas and a decision.
- `make test` passes.
