---
status: resolved
context_rev: 2
priority: P0
updated: 2026-09-14T23:40:13Z
summary: Make dependency revisions signal consumer-relevant semantic changes rather than every edit.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Finding

The current every-write revision rule makes cosmetic edits, evidence updates, and priority changes stale every pinned dependent even when no relied-upon assumption changed. This creates false-positive reconciliation work that grows with the graph.

# Decision

Rename the pinned field to `context_rev`. The eight-byte-per-header and pin-suffix migration cost is justified because `rev` normally implies an edit counter, while this number means only “a reconciled consumer must reread after this changed.”

Increment `context_rev` for a changed assumption, decision, invariant, interface, or other consumer-relevant context. Refresh `updated` for every mutation, but do not increment `context_rev` for cosmetic edits, evidence or history additions, status moves, priority or `next` changes, or equivalent local workflow updates. Use Git for edit history. When uncertain, increment it if a reasonable previously reconciled consumer should reread the node.

# Result

Migrated the skill, current graph, documentation, query recipes, and validation to `context_rev`. The graph validator rejects the obsolete `rev` field and requires `context_rev` pins for context-bearing dependency edges.
