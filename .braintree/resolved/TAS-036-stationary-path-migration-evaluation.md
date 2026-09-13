---
context_rev: 2
priority: P3
updated: 2026-09-11T22:20:08Z
summary: Retain authoritative status directories; hybrid evidence does not justify stationary paths or database-owned workflow metadata.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

# Outcome

Decide whether evidence warrants replacing authoritative status-directory moves with stationary paths and a database-owned workflow field.

# Done when

The evaluation compares measured Git conflicts and query costs with the current representation, defines a one-way authority migration if justified, or explicitly retains status directories.

# Result

Retain status directories. The completed hybrid audit records zero active claims
and no observed remaining status-rename or metadata-conflict churn; claims and
serial integration already prevent concurrent same-node status edits. The live
sidecar has 47 indexed nodes, 59 edges, and zero stale pins, but it supplies no
evidence that workflow fields need a second authority.

`make storage-comparison` still reports directory authority as `R100` over two
paths, zero body reads for the 25-node active query, zero different-node merge
conflicts, and no stale view. Stationary metadata reduces a transition to one
modified path but scans all 100 canonical files; moving `status`, `priority`,
or `next` into SQLite would also violate the single-authority contract and make
ordinary Obsidian editing dependent on sidecar reconciliation.

Reconsider only after measured production Git churn shows material
rename/edit conflicts despite claims and serial integration, and a proposed
migration defines one-way authority, recovery, Obsidian behavior, and a full
validation/rollback plan. No path or workflow-field migration is warranted.
