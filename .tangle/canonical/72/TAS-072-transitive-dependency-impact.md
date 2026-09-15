---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Add `tangle impact ID` so direct and transitive dependency impact is one call in dependency order.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

`SKILL.md` tells the reader that indirect impact requires repeating the exact
pinned-backlink search through returned nodes. That is N round trips for a
traversal the sidecar can compute once.

# Outcome

`tangle impact ID` lists every direct and transitive dependent of the target
in dependency order, with each edge's pinned revision and the target's current
revision, so stale consumers are visible in one answer.

# Done when

- The query is transitive and cycle-safe over the derived context edges.
- Output is dependency-ordered and names pinned versus current revisions.
- Tests cover a chain, a diamond, and a cycle.
- `make test` passes.

# Result

`src/tangle/index.py` derives the answer from Markdown alone, so
`tangle impact ID` needs no sidecar and cannot drift from the vault. It walks
the reverse of the canonical `CONTEXT_RELATIONS` edges breadth-first from the
target, reporting each distinct dependent edge once with its depth, relation,
pinned revision, the dependency's current revision, and the shared
`context_pin_problem` verdict. A visited set makes a dependency cycle terminate,
and a cycle back to the target does not list the target as its own dependent.
Rows sort by dependency distance then identity, so the nearest stale consumers
come first, and the header prints the target's current `context_rev`.

`tests/test_tangle_index.py` covers a chain, a diamond with both paths to one join
node, and a three-node cycle, plus navigation-edge filtering, zero dependents,
and an unknown node; `tests/test_tangle_foundation.py` covers dispatch and the
argument error. `make test` passes.
