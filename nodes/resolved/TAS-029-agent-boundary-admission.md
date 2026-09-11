---
context_rev: 1
priority: P1
updated: 2026-09-11T12:01:55Z
summary: Require durable execution-memory value beyond resumability before admitting a task node.
---

# Context

Area [[IDX-001-execution-graph]].

# Outcome

Independent resumability is necessary but insufficient for a task node: it must also retain durable execution-memory value. Incidental cleanup, a single failed check, mechanical follow-up, and agent, write-set, or handoff boundaries alone do not justify nodes. A fresh worker may continue the same graph node because agents and nodes are not one-to-one.

# Done when

Admission and decomposition guidance, tests, and documentation express these rules, and the prior whitespace-remediation task is assessed for removal as work that never crossed admission rather than retained as durable history.

# Result

Admission now requires durable execution-memory value beyond independent resumability; worktree slices and fresh workers remain within an assigned node unless that threshold is met. The whitespace-remediation node was removed as graph noise, with no remaining backlinks.
