---
context_rev: 1
priority: P2
updated: 2026-09-12T13:58:00Z
summary: Define a non-node commit path for mechanical changes so a one-line edit need not spawn a node or an untracked commit.
next: State in SKILL.md and AGENTS.md that a mechanical change with no independent outcome is recorded in the enclosing node or committed with a Refs reference instead of being admitted as a node.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R6 from Tangle `THO-007-braintree-friction-tui-session` F1: the
node-admission rule rejects mechanical cleanup, while `AGENTS.md` rejects an
untracked commit, so a one-line build-config change forces either node sprawl or
a review-rejected commit.

# Outcome

A mechanical change with no independently resumable outcome has a sanctioned
commit path that references the enclosing node without creating a leaf.

# Done when

- `SKILL.md` states that such a change lives in the enclosing node's `next`/result or commits with a `Refs` reference to it.
- `AGENTS.md` states the matching commit convention.
- `make test` passes, including the `SKILL.md` contract assertions.
