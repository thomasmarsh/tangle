---
context_rev: 1
priority: P1
updated: 2026-09-12T15:09:27Z
summary: Add `braintree impact ID` so direct and transitive dependency impact is one call in dependency order.
next: Add a transitive dependency-impact query over the derived context edges.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

`SKILL.md` tells the reader that indirect impact requires repeating the exact
pinned-backlink search through returned nodes. That is N round trips for a
traversal the sidecar can compute once.

# Outcome

`braintree impact ID` lists every direct and transitive dependent of the target
in dependency order, with each edge's pinned revision and the target's current
revision, so stale consumers are visible in one answer.

# Done when

- The query is transitive and cycle-safe over the derived context edges.
- Output is dependency-ordered and names pinned versus current revisions.
- Tests cover a chain, a diamond, and a cycle.
- `make test` passes.
