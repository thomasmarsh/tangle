---
context_rev: 1
priority: P3
updated: 2026-09-12T12:40:14Z
summary: SKILL.md defines the next direct-child test and contrasts a planned dependency and requested plans with genuinely blocked work.
next: Define the direct-child test operationally in SKILL.md and add the blocked-versus-proposed example.
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
