---
status: proposed
context_rev: 3
priority: P0
updated: 2026-09-14T23:40:13Z
summary: Implement serialized local proposal acceptance and recovery.
next: Implement local integration, terminal evidence, and crash recovery.
---

Parent [[TAS-193-same-directory-graph-contribution-intake]].

# Context

Gated on [[TAS-196-local-proposal-reconciliation-planning]].

Acceptance is the only path in the local proposal mode that may make a contribution canonical. Follow the exact Git and filesystem transaction boundary settled by the v1 definition; do not weaken it to make a partial apply convenient.

# Outcome

One local integrator can accept a fully decided proposal set exactly once, while racing integrators, moved bases, failed validation, and crashes leave no ambiguous or partially canonical graph state.

# Done when

- `integrate --dry-run` consumes a reconciliation plan and explicit decision artifacts, validates the symbolic candidate, and changes neither canonical Markdown nor terminal metadata.
- Apply acquires a same-host integration lease, reruns the complete canonical-store hash census, rechecks expected Git head and every operation precondition, verifies plan and proposal digests, and refuses unresolved or stale components. The lease provides exclusion only, never authority.
- Permanent node IDs use the stable contract's lowercase type prefix and exact 128-bit Crockford Base32 payload and are generated only for an acceptance attempt; no shared numeric sequence is needed for new-format nodes. One real host timestamp is materialized at acceptance, and compound create, amend, transition, advance, supersede, retire, or restructure operations apply entirely or not at all when v1 supports them.
- The exact candidate passes plain `tangle check` and all gates required by the accepted graph-only change before the specified canonical boundary is crossed. Unsupported or unbound repository effects fail closed.
- A unique acceptance record captures the integration ID, selected proposal digests, dispositions, ID mappings, decision evidence, gate evidence, and plan hash without attempting to contain its own commit hash.
- Terminal receipts are idempotent and recoverable from canonical acceptance evidence after a crash. Conflicting terminal dispositions are errors; `needs-revision` remains nonterminal and points to a new proposal when revised.
- A moved head or failed compare-and-swap publishes no terminal receipt or canonical mapping and forces reconciliation against the winner. Temporary candidates and failed attempts cannot masquerade as pending durable proposals, and generated views cannot publish an unaccepted candidate.
- After successful canonical acceptance, the index delta and affected Markdown views publish from the accepted snapshot. Projection failure is reported and recoverable by the next full census without changing which graph state is authoritative.
- Multi-process tests race submitters and integrators, inject failures before and after the canonical boundary, verify late ID behavior and recovery, and prove compound operations never become partially visible.
