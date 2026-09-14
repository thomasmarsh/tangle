---
status: resolved
context_rev: 1
priority: P0
updated: 2026-09-14T23:40:13Z
summary: Implement the external SQLite sidecar identity, schema, atomic claims, leases, and ID allocation.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

Same-host worktrees share one project-identity-keyed, untracked SQLite sidecar that atomically allocates IDs and leases exclusive node claims.

# Done when

Commands initialize and locate the sidecar safely, use transactions for allocation and claims, enforce lease expiry and base-hash checks, and reject unsupported cross-host/network use clearly.

# Result

`scripts/bt` keeps its SQLite WAL database outside the repository under a stable Git-common-directory hash (with isolated `BT_SIDECAR_DIR` and `BT_PROJECT_ID` overrides for tests). It owns only `id_sequences` and expiring `claims`; allocation uses `BEGIN IMMEDIATE`, and claim renewal requires the same agent and base content hash. `tests/bt-foundation.sh` verifies initialization, WAL, monotonic per-prefix allocation, conflicting-hash rejection, release, expiry, and strict argument handling.
