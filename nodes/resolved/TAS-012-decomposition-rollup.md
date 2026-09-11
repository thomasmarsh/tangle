---
context_rev: 2
priority: P1
updated: 2026-09-10T20:40:48Z
summary: Established just-in-time decomposition and evidence-based parent completion.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Finding

Atomic nodes permit recursive subplanning, but the skill does not define when decomposition is useful, how a parent selects its current frontier, or how child state affects parent completion. Without those rules, the graph can become many small plan files rather than an execution structure.

# Outcome

Define recursive decomposition without child catalogs, and make parent resolution depend on its own evidence rather than a child-count shortcut.

# Done when

The skill, public documentation, and graph checks define independently resumable children, a single deliberate frontier, and evidence-based parent completion.

# Result

Added just-in-time decomposition for independently resumable outcome, blocker, dependency, and verification boundaries. A coordinating task now records its own outcome and `Done when` criteria; its `next` selects one action or direct-child frontier. The roll-up requires parent evidence and resolves or explicitly disposes every created child, so resolved child state alone cannot close the parent. README, benchmark guidance, and contract checks cover the rule.
