---
context_rev: 1
priority: P2
updated: 2026-09-12T17:32:35Z
summary: State whether a worker may author the minimal primitive or seam a slice gate needs inside its declared write set, and when it must escalate.
next: Add the slice write-set authoring rule to the parallel-worktree contract in SKILL.md and pin it with a contract test.
---

# Context

Parent [[TAS-095-usage-feedback-hardening-round-four]].

Tangle `FBK-003` at `0.5.0+g64359e6`: an assigned slice whose gate required an
authored stop line and a spawn admission the compiled model did not provide,
while the write set covered only two packages. Neither `SKILL.md` nor the node
said whether a gate's needed primitive is in-scope authoring, a new node, or an
escalation, so the worker stopped mid-slice twice. Reproduced in
[[THO-013-round-four-usage-feedback-and-portfolio-analysis]] by reading the
contract: the parallel-worktree section names the write set, its verification,
and the handoff report, but no authoring rule, and no text matches `primitive`
or `seam`.

# Outcome

A worker continuing an assigned slice knows that a minimal primitive or seam
its gate or Done-when criterion needs is in-scope authoring inside the declared
write set, and which boundary instead requires escalation, so it does not stop
mid-slice to ask.

# Done when

- `SKILL.md` states that a worker may author the minimal primitive or seam a gate or Done-when criterion needs inside its declared write set, and records it in the node's result.
- `SKILL.md` states the escalation boundary: a change that alters a landed seam another node owns, or the public schema contract, is escalated rather than authored.
- `SKILL.md` states that a coordinating task names any primitive or seam its slice must introduce, so the worker does not have to infer it.
- A `SKILL.md` contract test pins the stated rule and `make test` passes.
