---
context_rev: 1
status: proposed
updated: 2026-09-14T22:58:32Z
summary: Reduce the mandatory Tangle skill hot path.
next: Identify invariant text that must remain in the mandatory core.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

The mandatory workflow instructions contain only universal safety and execution invariants; conditional detail is loaded on demand.

# Done when

- The core preserves admission, routing, dependency, mutation, and final-gate rules.
- Conditional coordination, migration, and authoring detail is routed through help topics.
- Contract tests demonstrate that a fresh worker can execute the normal path from the smaller core.
