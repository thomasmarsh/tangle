---
context_rev: 1
priority: P1
updated: 2026-09-11T12:40:54Z
summary: Verify hybrid-store correctness, recovery, and same-host worktree coordination.
next: Define isolated fixtures for claims, allocation, reindex, and stale-pin queries.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

Automated evidence demonstrates atomic coordination, derived-index recovery, and preserved Markdown graph integrity across real local worktrees.

# Done when

Tests cover contention, expired leases, hash mismatch, duplicate allocation prevention, rebuild after database deletion, FTS/backlinks/staleness, and unsupported deployment diagnostics.
