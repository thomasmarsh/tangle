---
context_rev: 1
status: proposed
updated: 2026-09-15T20:38:27Z
summary: Consolidate authoring helpers, the skill, and preserved-prose tests.
next: Design guarded create/progress/resolve/context-revision edit helpers that produce a reviewable patch.
---

Parent [[tas-10sn2b04x59bkd80j8h5hqp4tk-sequence-the-arch-md-section-7-replacement-in]].

# Context

ARCH.md sections 3, 4, and 7.4 consolidate authoring and instructions. Add
guarded edit helpers (create, record progress, resolve, revise context) that
load starting bytes, compute an edit plan, require an explicit semantic-change
choice, validate the prospective graph, check expected hashes under a short
writer lock, and apply through same-directory temporary files. Reduce SKILL.md
toward roughly 300-500 words by moving task-specific language into packets and
commands. Replace prose-preservation tests with behavioral scenarios where a
literal string is not the contract. Coordinate four intentional policy changes
that are not transparent refactors: mandatory claims, automatic index upkeep,
abbreviated inputs, and scoped diagnostics.

This overlaps prior commitments:
[[TAS-191-transactional-decomposition-authoring]] and
[[tas-4ysvfgkb6ytqbch8f5ae6qzt3w-collapse-the-test-skill-py-prose-lock-apparatus]]
own related slices; reference rather than duplicate.

# Outcome

Authoring helpers perform create, progress, resolve, and context revision
through reviewable, hash-guarded patches; the skill is short; prose-lock tests
are replaced by behavioral scenarios; and the four policy changes are settled
and applied.

# Done when

- The guarded edit helpers produce a reviewable patch, reject a conflicting
  expected hash, and leave a checkable intermediate state on a crash.
- SKILL.md is reduced toward its 300-500 word budget with conditional detail
  moved to commands, packets, and references.
- Prose-preservation tests are replaced by behavioral scenarios except where a
  literal string is the contract.
- Each of the four policy changes is settled (with a DEC or DEF where the
  contract needs one), applied, and tested.

# Scoping

Needs finer-grained scoping: yes. The edit helpers, skill reduction, test
replacement, and each policy change have separate acceptance and should be
separate children; several require a decision node first.
