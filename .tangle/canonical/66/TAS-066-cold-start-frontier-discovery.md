---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Added a tested `Frontier` query recipe that surfaces the current frontier in one command.
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

# Result

`nodes/index-map.md` carries a `Frontier` recipe:

```sh
rg --files-without-match '^next:.*\[\[' nodes/*/ 2>/dev/null | rg '/(active|proposed|blocked)/'
```

It lists the unfinished nodes whose `next` is an action rather than a
wikilinked child route, which is the current frontier: a coordinating node is
excluded while its `next` target appears. `SKILL.md` names the recipe in Read and
execute step 2 and in Common queries.

`tests/test_skill.py` covers it twice. One test builds a temporary vault with a
coordinating node whose `next` is a wikilink to `TAS-102-validate-manifests`, a
leaf, and a resolved node and asserts the frontier is the child and leaf only.
The other runs the recipe extracted from `index-map.md` against the live vault
and compares it with the frontier derived from the Markdown, so it cannot
silently drift as nodes move.

Evidence: `make test` passes.
