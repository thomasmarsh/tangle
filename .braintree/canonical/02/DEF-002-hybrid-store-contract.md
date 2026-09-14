---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Define authority, reconciliation, recovery, and deployment invariants for the hybrid graph store.
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

# Invariant

The external sidecar contains `nodes` (path, identity, type, summary, revision, content hash, indexed time), `edges` (source, relation, target, pinned revision), FTS content, `claims` (node, agent, base hash, lease expiry), and `id_sequences`. Every command reconciles a changed Markdown content hash before use; `bt reindex` reconstructs derived node, edge, and FTS state from Markdown. Database loss may lose leases or allocations but never durable knowledge.

Claims are atomic and accepted only when the lease and starting content hash match. Leases expire. A coordinator serially integrates worktree changes and rechecks dependency pins. The database is not committed, copied into synchronized/network filesystems, or treated as durable knowledge.
