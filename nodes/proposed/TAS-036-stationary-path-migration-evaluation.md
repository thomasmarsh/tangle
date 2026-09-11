---
context_rev: 1
priority: P3
updated: 2026-09-11T12:40:54Z
summary: Evaluate stationary Markdown paths and database-owned workflow metadata only after hybrid-store evidence exists.
next: Await the completed hybrid-store audit and measured status-transition churn.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

# Outcome

Decide whether evidence warrants replacing authoritative status-directory moves with stationary paths and a database-owned workflow field.

# Done when

The evaluation compares measured Git conflicts and query costs with the current representation, defines a one-way authority migration if justified, or explicitly retains status directories.
