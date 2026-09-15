---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Run the staged token and round-trip A/B comparing the pre-thrust state with the landed direct-answer surface.
disposition: superseded
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

The zero-live harness landed as `tangle benchmark staged`
(`src/tangle/staged_benchmark.py`, commit `c4cbd27`, `Refs: TAS-080`). It
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
(`tangle benchmark token --record --case composite --representation graph
--scale small --repetitions 1 --model MODEL --reasoning-effort low`, once from
`0e39f3a` and once from the landed checkout), run `tangle benchmark staged`
over the two records, and resolve this node with the deltas and the decision.

# Result

Superseded by [[DEC-009-retire-staged-live-token-ab]]; not executed.

No matched pre-thrust and landed sample pair was ever recorded. The node is
retired because the question it owned is answered by stronger, already-landed
evidence: the correctness-gated verb baselines and round-trip telemetry of
[[TAS-078-round-trip-telemetry-and-gates]], the recipe removal and skill-text
A/B of [[TAS-074-shrink-skill-to-commands]], and the held-out correctness-cost
surface of [[TAS-120-agent-memory-evaluation-program]]. A single live pair would
also fall below the two-round, three-sessions-per-arm standard of
[[DEC-004-compact-skill-text]]. The zero-live harness remains available for a
future authorized A/B.
