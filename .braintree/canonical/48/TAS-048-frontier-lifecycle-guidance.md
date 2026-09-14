---
status: resolved
context_rev: 1
priority: P3
updated: 2026-09-14T23:40:13Z
summary: SKILL.md defines the direct-child test and next forms, contrasts blocked with a proposed sibling, and permits a requested proposed plan.
---

# Context

Parent [[TAS-044-usage-feedback-hardening]].

Feedback findings F5, F6, and F7: the `next` grammar and direct-child test live
only in `graph_check.py`; `blocked` versus a dependency inside the same planned
tree is ambiguous; and "decompose just in time" does not distinguish a
user-requested proposed tree from speculative decomposition.

# Outcome

`SKILL.md` states the accepted `next` forms and the direct-child test, resolves
the `blocked` versus proposed-dependency boundary with a concrete example, and
permits a user-requested proposed tree subject to resolve-or-dispose.

# Done when

- `SKILL.md` defines a direct child as a node whose primary `Parent`/`Area` is
  the current node, and lists the accepted `next` forms.
- `SKILL.md` contrasts a `blocked` node that is missing external input with a
  proposed node gated on a sibling decision.
- `SKILL.md` distinguishes a requested proposed plan from speculative
  decomposition.
- `make test` passes, including any checker fixture added for the documented
  grammar.

# Result

`SKILL.md` now defines a direct child as a node whose primary `Parent`/`Area` is
the current node, lists the two accepted `next` forms (a plain action or one
`direct-child` link), contrasts `blocked` external input with a `proposed`
sibling gated on an in-graph decision, and allows a user-requested plan to be
created up front as `proposed` work subject to resolve-or-dispose.

Evidence:

- `SKILL.md` decomposition section carries the direct-child definition, `next`
  forms, blocked-versus-proposed contrast, and requested-plan allowance.
- `make test` passes; the TAS-047 trailing-text fixture is the checker fixture
  for the documented pin grammar.
