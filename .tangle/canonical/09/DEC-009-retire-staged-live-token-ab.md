---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Retire the staged live token/round-trip A/B; the direct-answer surface's cost and correctness are established by the landed zero-live gates and the memory-evaluation program.
---

Area [[IDX-001-execution-graph]].

# Decision

Retire the staged live token and round-trip A/B for the direct-answer surface.
The surface's always-loaded token cost and correctness are established by the
landed zero-live gates and the memory-evaluation program, so no live session
pair is required and no owner authorization is sought.

# Context

[[TAS-080-staged-token-ab]] would have run one matched live Codex session pair
(`--repetitions 1`, so n=1 per arm) comparing the pre-thrust commit `0e39f3a`
with the landed direct-answer surface. It never ran: the owner did not
authorize live model spend, and the before-anchor is now 127 commits behind
`HEAD`.

Three later evidence sources supersede its outcome:

- [[TAS-074-shrink-skill-to-commands]] recorded the recipe removal and a
  skill-text A/B.
- [[TAS-078-round-trip-telemetry-and-gates]] landed round-trip telemetry and a
  correctness-gated baseline for every direct-answer verb
  (`tangle benchmark verbs`).
- [[TAS-120-agent-memory-evaluation-program]] ran a preregistered 1,080-sample
  held-out correctness-cost evaluation with a monetary cost surface
  (`research/agent-memory-confirmatory-report.md`).

# Rationale

- A single live pair cannot support a keep/revise/revert decision:
  [[DEC-004-compact-skill-text]] requires a two-round A/B of at least three
  sessions per arm and forbids deciding on a single run, and the memory
  program's comparisons use bootstrap intervals.
- The `0e39f3a` before-anchor is stale by 127 commits, and the fixture hash
  embeds `SKILL.md` and `src/tangle`, so a delta would conflate the
  direct-answer surface with the whole memory program and other contract
  changes.
- The measurable payoff already landed: `SKILL.md` is smaller than the 13,481 B
  compact baseline [[DEC-004-compact-skill-text]] adopted, and
  [[TAS-078-round-trip-telemetry-and-gates]] gates each verb's exact answer.

# Consequences

- [[TAS-080-staged-token-ab]] is `resolved` with `disposition: superseded` and
  names this decision as its replacement.
- The direct-answer thrust [[TAS-068-direct-answer-surface]] and its theory
  [[THO-010-round-trip-reduction-theory]] roll up on this evidence.
- No live Codex spend is authorized by this decision; a future live A/B needs
  its own node and authorization.
