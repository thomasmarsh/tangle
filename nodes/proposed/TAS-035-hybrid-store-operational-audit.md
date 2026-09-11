---
context_rev: 1
priority: P2
updated: 2026-09-11T12:40:54Z
summary: Audit the completed hybrid store against its authority, durability, and Git-churn promises.
next: Review implementation evidence after the required hybrid-store children resolve.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

# Outcome

An integration audit establishes that no dual authority or tracked database state remains and that the command surface satisfies the decision.

# Done when

The audit records command, test, graph-check, ignore-rule, recovery, and worktree evidence, then recommends whether observed metadata churn justifies a future status migration.
