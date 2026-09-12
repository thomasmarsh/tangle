---
context_rev: 1
priority: P2
updated: 2026-09-12T15:09:27Z
summary: Add advisory `braintree next --rank` and clustering so frontier selection and hub grouping are direct answers.
next: Rank frontier candidates by priority, blocking power, and recency, and cluster members into advisory workstreams.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

The frontier answers "what is unfinished" but not "what should one actor take
next" or "which candidates belong to the same workstream." Those are graph and
lexical computations over data the sidecar already holds.

# Outcome

`braintree next --rank` orders frontier candidates by priority, transitive
blocking power, and recency, and `frontier --group` clusters candidates by
shared parent, area, and dependencies so a coordinator can assign disjoint
write sets. Both are advisory, never claims.

# Done when

- Ranking is deterministic and documented, with no model required.
- Grouping is advisory and bounded, and its output never becomes authority.
- Tests cover the ranking order and a two-workstream grouping.
- `make test` passes.
