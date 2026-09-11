---
context_rev: 2
priority: P0
updated: 2026-09-10T20:37:41Z
summary: Implemented durable root-hub routing and orphan-unfinished-node detection.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Finding

Correct but unreachable nodes will accumulate when discovery depends on knowing an identifier or search term in advance. Broad area resumption is not currently guaranteed to select the relevant work.

# Intended change

Keep `index-map.md` small and route it to durable `IDX` area or component hubs. Require each non-root node to have a primary `Parent` or `Area` relationship, and require every unfinished task to be reachable from a hub or deliberate focus route. Treat orphan unfinished nodes as graph-integrity failures while continuing to derive hub membership through backlinks instead of copied catalogs.

# Result

Added the `IDX-001` root hub, migrated former root nodes to its `Area` route, and made graph tests reject missing or multiple primary routes, cycles, and orphan unfinished nodes. The index and hubs contain routes only; membership remains backlink-derived.
