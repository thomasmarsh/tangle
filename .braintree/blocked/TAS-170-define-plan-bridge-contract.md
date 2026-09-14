---
context_rev: 1
updated: 2026-09-14T02:16:25Z
summary: Define a resumable source-plan bridge and reconciliation contract.
next: Answer the bridge identity, mapping, reconciliation, and rollback questions.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-168-characterize-legacy-plans]].
Gated on [[TAS-169-settle-plan-graph-authority]].

Start with an ordinary coordinating TAS rather than a new node type or mandatory schema. Add structure only when the pilots show that prose cannot support reliable resumption.

# Outcome

One source plan can be reviewed incrementally without rereading it wholesale or confusing source evidence, migration bookkeeping, and graph authority.

# Done when

- The bridge records the source path and a stable Git revision or content hash, its authority class, the scope reviewed, the current extraction frontier, reconciled sections, unresolved contradictions, and completion and rollback criteria.
- A compact mapping connects each reviewed source section to an existing owner, new admitted node, source-only disposition, deferred branch, or ignored stale history.
- The mapping is migration evidence rather than a copied task ledger.
- Extraction is reviewed and outcome-based: automatic retrieval may find and cite source sections but never turns headings, chunks, or inferred entities into authoritative nodes.
- The contract defines what happens when source-only narrative, not-yet-admitted work, an admitted operative fact, or duplicated graph-owned status changes.
- Full migration preserves the original document and normalizes meaning without destroying provenance.
- Another agent can resume intake from the bridge without loading the entire source plan.

# Blocked

Blocked by: project-owner choices about the durable shape and acceptable maintenance burden of a bridge.

Questions for the project owner:

1. Should one bridge represent one document, one plan family, or one migration campaign?
2. Is path plus Git revision sufficient source identity, or is a content or section hash required?
3. Should the section mapping live only in the bridge body, in an adjacent Markdown artifact, or in a derived disposable index?
4. How precisely must source spans be anchored when headings and prose are repeatedly rewritten?
5. What source changes are meaningful enough to demand reconciliation?
6. What exactly completes a partial or full migration, and what rollback must remain possible?
7. May a bridge introduce any new frontmatter or command surface, or should the first contract remain prose-only?

Unblocks when: the owner answers these bridge-policy questions after the authority direction is clear.
