---
context_rev: 1
priority: P2
updated: 2026-09-12T16:33:00Z
summary: Run the staged token and round-trip A/B comparing the pre-thrust state with the landed direct-answer surface.
next: Obtain owner authorization for one bounded, matched live Codex pair.
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

# Status

The zero-live harness landed as `braintree benchmark staged`
(`src/braintree/staged_benchmark.py`, commit `c4cbd27`, `Refs: TAS-080`). It
compares two `codex-session-token-v2` records of the same controlled task,
requires matched fixture generator, case, representation, scale, model, effort,
and CLI version, runs the record's exact-value `correctness` gate plus an
independent re-run over the raw session and answer when supplied, and reports
per-change token and round-trip deltas with a keep, revise, or revert decision.
It reuses the token benchmark's session parser for round trips, so a record that
predates the round-trip telemetry still reports counts. It makes no model calls,
so `make benchmark` stays zero-live.

Pending: no matched pre-thrust and landed sample pair exists to feed the
harness, and producing one needs one bounded live Codex session pair — model
spend the owner has not authorized. Once authorized, record both samples
(`braintree benchmark token --record --case composite --representation graph
--scale small --repetitions 1 --model MODEL --reasoning-effort low`, once from
`0e39f3a` and once from the landed checkout), run `braintree benchmark staged`
over the two records, and resolve this node with the deltas and the decision.

# Blocked

Blocked by the missing owner authorization for one bounded, matched live Codex
session pair on the account. Unblocks when the owner authorizes that pair; then
the two samples can be recorded and the A/B run.
