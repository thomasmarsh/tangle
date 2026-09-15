---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Fix or dispose the round-five Hekate feedback findings in lease lifecycle visibility and the coordinator closeout and verification contract.
---

# Context

Parent [[THO-014-round-five-usage-feedback-analysis]].

Hekate `FBK-005` and `FBK-006` verified in the parent at `0.5.0`
(`0.5.0+gd1a4b82`, re-checked at `ba362e3`). Hekate `FBK-001` through `FBK-004`
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

- [[TAS-100-lease-lifecycle-visibility]] — Hekate `FBK-005`.
- [[TAS-101-resolution-ownership-clarity]] — Hekate `FBK-006` gap 1.
- [[TAS-102-verification-evidence-contract]] — Hekate `FBK-006` gap 2.

# Result

All three round-five children are resolved and integrated serially by
coordinator-owned commits:

- `1232225` `fix(braintree): make lease lifecycle explicit and observable` —
  resolves TAS-100.
- `04656c2` `docs(skill): state coordinator resolution ownership` — resolves
  TAS-101.
- `8c8fd07` `docs(skill): require falsifiable verification evidence` — resolves
  TAS-102.

Done when: the lease default duration and renew-on-reclaim rule are stated with
remaining lease time visible and an `expired` result distinct from `no-op`
(TAS-100); `SKILL.md` states that the coordinator alone performs a coordinating
parent's resolving edit while a worker slice prepares closeout evidence only
(TAS-101); `SKILL.md` states that independent slice verification needs an
executing verifier or a coordinator-run gate transcript and that a no-execution
reviewer cannot be the sole sign-off (TAS-102). Every child carries a `# Result`
with test evidence; each child's `Done when` is satisfied by its resolved node.

Gate evidence: `braintree check nodes` → `graph check: passed (123 nodes)`
after each integration and at closeout; `make test` at closeout.

Limitations: TAS-101 and TAS-102 are contract-prose rules pinned by substring
tests; `braintree check` verifies node state, not writer identity or gate
transcripts, so it cannot enforce which actor performed a resolving edit or ran
a gate. TAS-100's `release` still reports `no-op` when a different agent's lapsed
claim is the node's only record.
