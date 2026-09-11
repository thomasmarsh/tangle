---
context_rev: 1
priority: P1
updated: 2026-09-11T12:40:54Z
summary: Implement rebuildable SQLite indexing of Markdown nodes, semantic edges, and full-text search.
next: Define parser inputs and `kg reindex` output invariants.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

Specialized commands reconcile changed Markdown hashes, rebuild derived node/edge/FTS tables, and provide graph discovery without replacing Markdown authority.

# Done when

Reindex recovery, backlinks, stale-pin discovery, traversal, and FTS queries are tested against the vault without persisting generated state in Git.
