---
context_rev: 1
priority: P1
updated: 2026-09-11T12:49:04Z
summary: Implemented rebuildable SQLite indexing of Markdown nodes, semantic edges, and full-text search.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

Specialized commands reconcile changed Markdown hashes, rebuild derived node/edge/FTS tables, and provide graph discovery without replacing Markdown authority.

# Done when

Reindex recovery, backlinks, stale-pin discovery, traversal, and FTS queries are tested against the vault without persisting generated state in Git.

# Result

`bt reindex` rebuilds node, edge, and FTS tables from Markdown; `search`,
`backlinks`, and `stale` reconcile first and return compact TOON. The sidecar
can be deleted and reconstructed without changing the vault. Isolated-vault
tests cover FTS, reverse edges, stale and missing pins, strict arguments, and
database-loss recovery.
