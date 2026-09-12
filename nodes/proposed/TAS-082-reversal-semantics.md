---
context_rev: 1
priority: P2
updated: 2026-09-12T16:40:00Z
summary: State whether reversing a partly-implemented task is an in-place update or a supersession, and what the node owes commits that named the old direction.
next: Add the reversal rule to the mutation guidance.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N1: a task's outcome can be reversed after part of it is implemented and
committed. `SKILL.md` offers both an in-place update and `disposition:
superseded` without saying which wins, and says nothing about the commit that
named the old direction.

# Outcome

`SKILL.md` states the reversal rule, so a worker that reverses a partly
implemented outcome does not have to choose between two defensible readings.

# Done when

- `SKILL.md` states when a reversed outcome is an in-place update (with a `context_rev` bump) versus a `superseded` disposition with a replacement link.
- `SKILL.md` states what the resolved node records about a commit that named the reversed direction.
- A contract assertion pins the new guidance and `make test` passes.
