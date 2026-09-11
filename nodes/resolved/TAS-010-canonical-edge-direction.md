---
context_rev: 1
priority: P0
updated: 2026-09-10T20:33:49Z
summary: Give every graph relationship one authoritative stored direction and derive its inverse.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Finding

Requiring a new child to update both itself and its parent creates a two-file mutation and two relationship copies that can disagree. This weakens the single-node mutation and low-contention properties of the design.

# Intended change

Store `Parent` on the child, `Depends on` on the consumer, and `Superseded by` on the obsolete node. Derive `Child`, backlink, and depended-on-by views with exact searches. Allow a parent to link a child only when the link expresses deliberate current intent, such as the execution frontier, rather than an exhaustive catalog.

# Result

Established and tested canonical ownership across the skill, documentation, and graph. Removed reciprocal child, parent-of, and indexed-by copies; `Indexes` remains on the routing map.
