---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: State the session-slice rule and whether clearing a blocker is a semantic context_rev bump.
next: State the session-slice rule and whether clearing a blocker is a semantic context_rev bump.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-024` at `0.6.0+g3bacaf5`: a frontier node's `# Done when` spanned
several sessions, and `SKILL.md` says one node may span sessions but never sizes a
session to a coherent slice, so read literally the rules push either toward no
progress or toward silently attempting every deliverable. Separately, `SKILL.md`
says never bump `context_rev` for a status move, leaving unclear whether a
`blocked`->`proposed` move that flips whether downstream increments may start is
a status move or a semantic change; the worker had to choose and recorded a bump
to `3`.

# Outcome

`SKILL.md` states that a frontier node whose `# Done when` cannot be met in one
session is advanced by the smallest coherent slice, with the remaining scope and
evidence recorded in the body and the node left `proposed` or `active` with a
`next` naming the first remaining action, and that unblocking is not completing;
it also states whether clearing a blocker bumps `context_rev`.

# Done when

- The session-slice rule is in the status/next section and pinned by a contract
  test.
- The blocked-to-proposed `context_rev` question is answered explicitly.
- The rule keeps one node/one outcome without adding a sizing ritual.
- `make test` passes.
