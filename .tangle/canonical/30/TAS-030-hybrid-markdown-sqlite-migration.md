---
status: resolved
context_rev: 1
priority: P0
updated: 2026-09-14T23:40:13Z
summary: Converted this graph project to a Markdown-canonical, SQLite-assisted local execution store.
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

This repository exposes a tested specialized command surface for an external local SQLite sidecar while preserving the Obsidian-readable Markdown graph as durable authority.

# Done when

The coordination sidecar, derived index/query path, skill and installation contract, and verification evidence are complete; all created child tasks are resolved or explicitly disposed.

# Result

The external, Git-common-directory-keyed SQLite/WAL sidecar now provides atomic
same-host ID allocation and expiring claims plus rebuildable Markdown-derived
node, edge, stale-pin, backlink, and FTS indexes. Markdown remains authoritative
for knowledge and workflow state and remains Obsidian-readable. All migration
children are resolved: automated verification covers contention, recovery,
worktrees, graph discovery, and deployment boundaries; the audit found no
evidence to justify stationary paths or database-owned workflow metadata.
