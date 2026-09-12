---
context_rev: 1
priority: P2
updated: 2026-09-12T14:18:00Z
summary: Reduce the cold-start cost of locating the current frontier, which now takes a multi-step orientation pass with no direct query.
next: Add a tested frontier query recipe that resolves coordinating nodes' `next` to the current frontier, and reference it from the Read and execute loop.
---

# Context

Area [[IDX-001-execution-graph]].

Dogfooding observation from the TAS-060 session. With no direct node pointer,
locating the current frontier took a full orientation pass: read `SKILL.md`,
read `nodes/index-map.md`, enumerate the unfinished nodes, open the root hub
[[IDX-001-execution-graph]], derive its members by `Parent`/`Area` backlink,
then follow each coordinating node's `next`. `index-map.md` offers an
`Unfinished` recipe but no recipe that resolves coordinating nodes' `next` to
the actual frontier, and the hub deliberately lists no members, so a cold agent
must reconstruct the chain by hand before it can start work.

# Outcome

A cold agent with no pointer locates the current frontier in one documented
query, without opening the hub, the parent chain, and the unfinished list by
hand.

# Done when

- `index-map.md` or `SKILL.md` names a query that surfaces the coordinating
  node's `next` target — the frontier — directly.
- The recipe is tested so it cannot silently drift as nodes move.
- `make test` passes.
