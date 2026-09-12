---
context_rev: 1
priority: P2
updated: 2026-09-12T21:30:00Z
summary: Fix or dispose the round-five Tangle feedback findings in lease lifecycle visibility and the coordinator closeout and verification contract.
next: "[[TAS-101-resolution-ownership-clarity]]"
---

# Context

Parent [[THO-014-round-five-usage-feedback-analysis]].

Tangle `FBK-005` and `FBK-006` verified in the parent at `0.5.0`
(`0.5.0+gd1a4b82`, re-checked at `ba362e3`). Tangle `FBK-001` through `FBK-004`
are already fixed or admitted under
[[TAS-095-usage-feedback-hardening-round-four]] and are not in scope here.

# Outcome

Every confirmed round-five finding is fixed or explicitly disposed, with
regression tests where behavior changes.

# Done when

- The lease default duration and renew-on-reclaim rule are stated, and a claim that outlives its lease is distinguishable from one never held.
- `SKILL.md` states that the coordinator resolves a coordinating parent and that a worker slice prepares closeout evidence only.
- `SKILL.md` states the falsifiable evidence an independent slice verification needs.
- Every child is resolved or disposed with rationale.
- `make test` passes.

# Children

- [[TAS-100-lease-lifecycle-visibility]] — Tangle `FBK-005`.
- [[TAS-101-resolution-ownership-clarity]] — Tangle `FBK-006` gap 1.
- [[TAS-102-verification-evidence-contract]] — Tangle `FBK-006` gap 2.
