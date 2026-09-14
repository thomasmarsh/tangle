---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Theory: moving graph reasoning into direct `braintree` answers reduces client round trips and skill tokens without weakening correctness.
---

# Question

Parent [[TAS-068-direct-answer-surface]].

Do direct CLI answers for the core graph questions reduce client round trips and
the always-loaded `SKILL.md` token cost without weakening correctness?

# Hypothesis

The client's round trips are dominated by re-deriving graph facts that
`braintree` already holds: the frontier, a node's graph view, and dependency
impact. `SKILL.md` encodes those derivations as prose and shell recipes loaded
in every session. Moving each derivation behind one deterministic verb should
remove shell round trips, shrink the always-loaded contract, and keep every
answer equal to the Markdown derivation. Lowest-risk, highest-leverage changes
come first so the theory is tested before riskier retrieval, reconciliation, or
model work.

# Prediction

Each direct-answer verb replaces several shell calls with one bounded answer,
and the skill text shrinks in lockstep. Semantic retrieval is not required for
the reduction and stays optional under
[[DEC-006-semantic-layer-capability-boundary]].

# Test

- Staged comparison: [[TAS-080-staged-token-ab]].
- Round-trip telemetry: [[TAS-078-round-trip-telemetry-and-gates]].
- Owning thrust: [[TAS-068-direct-answer-surface]].

# Evidence

The isolated staged live A/B ([[TAS-080-staged-token-ab]]) was retired as
superseded by [[DEC-009-retire-staged-live-token-ab]], so the theory is decided
from landed evidence rather than a live pair:

- Always-loaded token cost: the recipe removal of
  [[TAS-074-shrink-skill-to-commands]] and the later consolidation left
  `SKILL.md` at 12,669 B, below the 13,481 B compact baseline adopted by
  [[DEC-004-compact-skill-text]], whose own two-round A/B cut median benchmark
  tokens 23.5%.
- Round trips: [[TAS-078-round-trip-telemetry-and-gates]] replaced the
  multi-step shell recipes for the frontier and dependency impact with the
  single `braintree frontier`, `braintree node`, `braintree impact`, and
  `braintree orient` verbs, and records tool-call and shell-call counts.
- Correctness: each direct-answer verb has an exact-value case and checked-in
  baseline in `braintree benchmark verbs`, and `make test` passes.

# Conclusion

Supported for the always-loaded contract: the direct-answer surface replaces
multi-call recipes with one verb each and the skill text is smaller, with
correctness held by the verb baselines. The magnitude of the client round-trip
reduction is established structurally and from telemetry, not from a matched
live pair, which was retired by [[DEC-009-retire-staged-live-token-ab]].
