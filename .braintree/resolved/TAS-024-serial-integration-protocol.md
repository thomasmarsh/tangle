---
context_rev: 1
priority: P1
updated: 2026-09-11T11:31:23Z
summary: Define serial integration and reconciliation rules for parallel worker branches.
---

# Context

Parent [[TAS-021-parallel-agent-hardening]].

# Outcome

Each worker keeps a node's content and status move coherent in one commit; the coordinator integrates worker branches serially, rejects or manually reconciles upstream changes to the same assigned node, and runs graph integrity plus dependency-staleness checks after each integration.

# Done when

The skill gives executable worker and coordinator steps, and focused assertions cover coherent commits, serialized integration, same-node divergence, graph validation, and stale dependency discovery.

# Result

Added the worker handoff evidence and write-set checks, serial coordinator integration, same-node and divergent-status reconciliation boundary, per-integration graph and exact dependency checks, and integrated-child parent-resolution barrier. Focused skill assertions pass.
