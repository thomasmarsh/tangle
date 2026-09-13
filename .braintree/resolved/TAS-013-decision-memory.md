---
context_rev: 1
priority: P1
updated: 2026-09-10T20:43:16Z
summary: Give durable decisions and settled knowledge an explicit compact representation and lifecycle.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Finding

The model promises durable decisions but does not name a decision node convention or preserve the minimum rationale needed to understand one later. A resolved definition or decision can also be mistaken for obsolete knowledge even though disposition is the intended validity signal.

# Intended change

Add a `DEC` convention with concise `Decision`, `Rationale`, and `Consequences` sections. Clarify that directory status describes the work of forming a knowledge node: a resolved definition or decision remains current unless `disposition: deprecated` or `disposition: superseded` says otherwise.

# Result

Added [[DEC-001-decision-node-convention]], the lifecycle rule, documentation, and contract checks. The resolved decision node demonstrates current settled knowledge without duplicating task authority.
