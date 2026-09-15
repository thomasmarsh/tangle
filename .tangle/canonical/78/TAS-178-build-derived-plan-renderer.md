---
status: proposed
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Build a one-way conventional plan renderer if justified.
next: Implement and evaluate the decided one-way conventional-plan projection.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-177-decide-derived-plan-rendering]].

This node is resolved only if rendering is admitted; otherwise it is disposed under the coordinating task.

# Outcome

Tangle can present a cohesive long-form plan to plan-preferring humans and LLMs while the graph remains the only editable execution authority.

# Done when

- The renderer includes the decided goals and narrative, current frontier, sequenced proposed work, operative decisions and dependencies, completed outcomes, and deferred or disposed branches.
- Source node IDs, revisions, and complete input hashes make the projection auditable and automatically invalidatable.
- A conspicuous generated marker states that edits are discarded and never reconciled into the graph.
- Regeneration deterministically replaces the prior view without changing authoritative nodes.
- Token or size bounds and truncation reports follow the settled contract.
- Tests cover current, historical, disposed, stale, and large-graph projections.
- Evaluation shows whether the rendering improves comprehension or compatibility for its named consumers over exact graph queries.
