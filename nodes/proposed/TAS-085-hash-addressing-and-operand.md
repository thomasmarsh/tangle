---
context_rev: 1
priority: P2
updated: 2026-09-12T16:40:00Z
summary: Document or implement the accepted node addressing and the exact `braintree hash` operand the claim records, and state whether the frontier transition belongs to the claimed edit.
next: Fix the addressing and hash operand contract and state the frontier-transition ordering.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N5: the worktree handoff gives a worker a direct node path, but `braintree hash`
rejects a path and accepts only a bare ID or filename stem, and `SKILL.md` never
states the accepted form. N6: `braintree hash` prints a labelled two-line
object while the skill calls it "the base hash" and says to pass "that same
starting value"; the claim accepts either the whole block or the bare
`content_hash` as an opaque operand, so the recorded value is ambiguous. N7: the
skill says to hash and claim before editing but never says whether a node's own
frontier transition (the status move and `# Context` edit that takes the
frontier) precedes the claim or belongs to the claimed edit, and which content
the recorded base hash names.

# Outcome

One documented, unambiguous hash and claim contract.

# Done when

- `braintree hash`, `claim`, and `release` accept the node path the handoff gives a worker, or `SKILL.md` states the accepted forms next to each command and in the worktree contract.
- `braintree hash` prints a bare digest, or `SKILL.md` states that the `content_hash` field is the operand and shows it in the hash, claim, and release examples.
- `SKILL.md` states whether the frontier transition precedes the claim or is part of the claimed edit, and which content the base hash names.
- A path-shaped unknown-node error suggests the accepted forms.
- Regression tests cover the chosen addressing and operand behavior and `make test` passes.
