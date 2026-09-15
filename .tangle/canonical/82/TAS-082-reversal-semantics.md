---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: A partly implemented reversal updates the same node in place with a context_rev bump, and supersedes only when the outcome moves to a different node.
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

# Result

Took the documentation branch: the rule reconciles two contracts that already
existed, so it required no new mechanism or checker behavior.

`SKILL.md` mutation rules now state the discriminator and the commit record:

- In place while the same node and scope still own the outcome: rewrite the
  outcome in the same node and bump `context_rev`, because a pinned consumer
  must reread the changed direction.
- Supersede only when the outcome moves to a different node: move to
  `resolved`, set `disposition: superseded`, record the replacement as a
  canonical `Superseded by` link in the body, and search remaining backlinks.
  Deprecation follows the same resolved-node shape with `disposition:
  deprecated`.
- A reversal records the commit that named the reversed direction — short SHA
  and subject — in the node body, with whether that commit's change was kept,
  reverted, or replaced. The reversal lands in the node and a new commit; the
  earlier commit is never rewritten, amended, or force-pushed.

The discriminator follows the existing admission rule, which already prefers
updating a node when new information advances the same outcome, and the
canonical `Superseded by` direction, which already places the replacement link
on the obsolete node.

Evidence:

- `SKILL.md` mutation rules carry the in-place versus supersession
  discriminator and the reversed-direction commit record.
- `test_skill_reversal_contract` pins the guidance.
- `make test` passes.
