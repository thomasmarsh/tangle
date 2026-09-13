---
context_rev: 1
updated: 2026-09-12T15:10:30Z
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

No samples recorded yet.
