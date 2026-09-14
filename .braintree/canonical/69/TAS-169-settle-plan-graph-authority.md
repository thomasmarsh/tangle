---
status: blocked
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Settle coexistence modes and give every mutable plan or graph fact one owner.
next: Answer the coexistence and authority questions in the blocker.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-168-characterize-legacy-plans]].

The expected artifact is a settled DEC informed by the representative-plan evidence, not an informal convention hidden in implementation.

# Outcome

A decision defines the recommended default and the authority of narrative, requirements, acceptance criteria, decisions, status, next actions, blockers, dependencies, and history in every supported coexistence mode.

# Done when

- The decision defines snapshot or archived-plan migration, living-specification hybrid, full migration, and any deliberately limited plan-led overlay.
- It states when a source plan becomes read-only, whether permanent hybrid operation is supported, what completes a migration, and whether any change is synchronized back into the source.
- Braintree owns admitted execution status, next actions, blockers, dependencies, and pinned operative decisions.
- The decision specifies how requirements and acceptance criteria move or remain authoritative without creating two editable owners.
- A generated conventional plan is explicitly derived and never an independent authority.
- The default recommendation and exceptions are justified by the corpus and pilot needs.

# Blocked

Blocked by: project-owner choices that determine the product's intended coexistence policy.

Questions for the project owner:

1. Should the default be archived-plan migration, a living-specification hybrid, or full migration?
2. May a source plan remain authoritative for narrative, requirements, or acceptance criteria after related work enters Braintree?
3. At what event should the source plan or a section of it become read-only?
4. Should permanent hybrid operation be a first-class supported mode or only a migration stage?
5. Should any graph change be written back to the source, or should all graph-to-plan views be derived one-way?
6. Is a plan-led overlay, where Braintree records only intake state and no mirrored task status, worth supporting?
7. Which compatibility obligations to existing human or LLM workflows constrain the authority split?

Unblocks when: the owner answers these policy questions sufficiently for the work to settle a DEC after the corpus evidence is available.
