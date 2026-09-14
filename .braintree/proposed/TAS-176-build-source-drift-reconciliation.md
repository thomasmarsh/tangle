---
context_rev: 1
updated: 2026-09-14T02:16:27Z
summary: Build source-drift detection and reconciliation if justified.
next: Implement and verify the decided source-drift reconciliation surface.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-175-decide-source-drift-policy]].

This node is resolved only if automated support is admitted; otherwise it is disposed under the coordinating task.

# Outcome

Reviewed source changes are classified against the authority contract without silently copying state between the plan and graph.

# Done when

- The implementation detects the decided file or section identity changes and cites the old and new source evidence.
- Source-only narrative changes require no graph mutation.
- Not-yet-admitted work is queued for later review rather than automatically admitted.
- A change contradicting an admitted operative fact is reported as an explicit conflict with its current owner.
- A plan checklist edit for graph-owned work is reported as an authority violation.
- Formatting-only, moved-section, renamed-file, deleted-source, unavailable-source, and uncommitted-source cases follow the settled policy.
- Results are bounded, auditable, offline under the promised mode, and never treated as authorization.
- Tests demonstrate meaningful drift, benign drift, conflicts, missing sources, and idempotent reconciliation.
