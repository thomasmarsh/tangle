---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State that the coordinator resolves a coordinating parent as a graph action and that a worker slice prepares closeout evidence only.
---

# Context

Parent [[TAS-099-usage-feedback-hardening-round-five]].

Hekate `FBK-006` gap 1 at `0.5.0+gd1a4b82`: an orchestration harness ran a
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

# Result

`SKILL.md`'s parallel worktree contract now carries a resolution-authority
bullet beside the existing coordinator-integrates clause. It states that
resolution authority is the coordinator's: after required children are
integrated, the coordinator alone performs a coordinating parent's resolving
edit — moving it to `resolved`, writing the outcome's evidence and limitations,
and removing `next`. It states the complementary boundary: a worker slice
prepares closeout evidence only (its result, limitations, and test and
dependency evidence) and never moves the coordinating parent to `resolved`, so a
delegated closeout task stops at the handoff and leaves the resolving edit to
the coordinator.

Evidence: `tests/test_skill.py::test_skill_resolution_claim_contract` pins the
new text via `_RESOLUTION_CLAIM_CONTRACT`. `braintree check nodes` and
`make test` pass.

Limitations: the rule is stated as contract prose and pinned by substring test
only; nothing in `braintree check` enforces which agent performs a resolving
edit, because the vault records node state and not writer identity. No vault
node had a pinned `Depends on [[TAS-101-resolution-ownership-clarity]]` edge, so
the resolution changes no consumer pin.
