---
context_rev: 1
priority: P2
updated: 2026-09-12T21:14:39Z
summary: State that the coordinator resolves a coordinating parent as a graph action and that a worker slice prepares closeout evidence only.
next: State the coordinator-resolves-parent and worker-closeout-evidence rule in the parallel-worktree contract in SKILL.md, then pin it with a contract test.
---

# Context

Parent [[TAS-099-usage-feedback-hardening-round-five]].

Tangle `FBK-006` gap 1 at `0.5.0+gd1a4b82`: an orchestration harness ran a
worker "resolution slice" to close findings and resolve the parent, while
`SKILL.md` says "the coordinator integrates child evidence, reconciles upstream
change, and alone resolves a coordinating parent after all required child work
is integrated". Reproduced in
[[THO-014-round-five-usage-feedback-analysis]] by reading the contract: the
coordinator clause exists, but no text says a worker slice prepares closeout
evidence only, and the word `closeout` does not appear. Because the resolving
edit was also a status move plus `next` removal, the boundary between a
coordinator graph action and a delegated writer was left to inference.

# Outcome

Resolution authority is unambiguous: a coordinating parent is resolved by the
coordinator after its required children are integrated, and a worker slice
contributes closeout evidence but never performs the parent's resolving edit.

# Done when

- `SKILL.md` states that the coordinator alone performs a coordinating parent's resolving edit — the status move, the outcome evidence and limitations, and the `next` removal — once required children are integrated.
- `SKILL.md` states that a worker slice may prepare closeout evidence (result, limitations, and test and dependency evidence) but may not move the coordinating parent to `resolved`.
- A `SKILL.md` contract test pins the stated rule and `make test` passes.
