---
context_rev: 1
priority: P0
updated: 2026-09-11T12:40:54Z
summary: Implement the external SQLite sidecar identity, schema, atomic claims, leases, and ID allocation.
next: Design the portable `kg` command and sidecar location contract.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

Same-host worktrees share one project-identity-keyed, untracked SQLite sidecar that atomically allocates IDs and leases exclusive node claims.

# Done when

Commands initialize and locate the sidecar safely, use transactions for allocation and claims, enforce lease expiry and base-hash checks, and reject unsupported cross-host/network use clearly.
