---
context_rev: 1
priority: P0
updated: 2026-09-14T18:55:52Z
summary: Deliver same-directory graph contribution intake.
next: "[[TAS-195-immutable-local-change-submission]]"
---

Parent [[TAS-192-deliver-opt-in-parallel-graph-mutation-and]].

# Context

Gated on [[DEF-003-opt-in-change-intake-protocol-v1]].

This is the first and highest-priority delivery phase. It supports several clients in one working directory by making their graph contributions append-only and non-authoritative until one local integrator accepts them. It does not promise safe concurrent source editing or accept an unbound repository effect.

# Outcome

Multiple same-directory clients can submit, compare, disposition, and accept graph-only contributions without concurrently editing canonical node files, while a single writer can continue using the existing direct workflow unchanged.

# Done when

- Immutable local proposal submission and inspection implement the v1 contract.
- Read-only reconciliation detects exact duplicates, deterministic structural overlap, stale assumptions, and unknown semantic cases against the current canonical graph.
- Serialized local acceptance rechecks preconditions, validates the complete candidate, records dispositions and recovery evidence, and cannot partially accept a compound operation.
- The CLI derives mechanical metadata and asks for semantic input only for an ambiguous component.
- Conditional documentation and adversarial multi-process tests demonstrate both the opt-in workflow and the unchanged simple path.
- All direct children are resolved or deliberately disposed, their evidence is rolled up here, and the repository gates named by those children pass.
