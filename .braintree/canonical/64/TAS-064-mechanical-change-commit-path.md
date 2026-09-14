---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Define a non-node commit path for mechanical changes so a one-line edit need not spawn a node or an untracked commit.
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

# Result

`SKILL.md` now states in the node-admission section that a mechanical change
with no independently resumable outcome lives in the enclosing node's `next` or
result, or names that node in a `Refs:` footer when it needs its own commit.
`AGENTS.md` carries the matching conventional-commit bullet.

Evidence:

- `test_mechanical_change_commit_path` in `tests/test_skill.py` asserts the
  mechanical-change contract in both `SKILL.md` and `AGENTS.md`.
- `make test` passes.
