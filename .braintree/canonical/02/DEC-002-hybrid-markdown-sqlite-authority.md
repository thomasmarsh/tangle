---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Keep durable knowledge in Markdown and add an external SQLite sidecar for indexes and atomic local coordination.
---

# Context

Area [[IDX-001-execution-graph]].

# Decision

Adopt a hybrid store. Markdown remains canonical for durable node prose, semantic wikilinks, `context_rev`, and dependency pins. An untracked SQLite sidecar is derived authority for parsed nodes, edges, and FTS, and initial authoritative state for same-host claims, expiring leases, and numeric ID allocation. Expose both through specialized `bt` commands; do not require agents to manipulate database files or SQL directly.

# Rationale

SQLite supplies B-tree indexes, transactions, recovery, and query support; a custom B-tree would duplicate weaker infrastructure. Git-tracked Markdown remains portable and Obsidian-readable, while cross-worktree claims and allocation need atomic shared state.

# Consequences

No field has dual authority. The sidecar is external, untracked, keyed by stable project identity rather than worktree path, and must be rebuildable from Markdown except operational claims and allocations. WAL is supported only for processes on one host and a local filesystem; use PostgreSQL for cross-host coordination. Retain status directories initially; reconsider stationary paths and database-owned `status`, `priority`, or `next` only after measured churn warrants it. This revises the file-only premise of [[TAS-017-stationary-canonical-storage]] without changing its current representation yet.
