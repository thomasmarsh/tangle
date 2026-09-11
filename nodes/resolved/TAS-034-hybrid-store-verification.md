---
context_rev: 1
priority: P1
updated: 2026-09-11T21:18:11Z
summary: Verify hybrid-store correctness, recovery, and same-host worktree coordination.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

Automated evidence demonstrates atomic coordination, derived-index recovery, and preserved Markdown graph integrity across real local worktrees.

# Done when

Tests cover contention, expired leases, hash mismatch, duplicate allocation prevention, rebuild after database deletion, FTS/backlinks/staleness, and unsupported deployment diagnostics.

# Result

`tests/kg-verification.sh` covers those cases with disposable sidecars and two real local worktrees; it passes in `make test`. Live initialization, reindex, FTS search, backlinks, stale-pin, and status queries passed using the external sidecar; it reports 47 nodes, 59 edges, zero stale pins, and zero active claims.
