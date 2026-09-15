---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State the falsifiable evidence independent slice verification needs, so a no-shell reviewer cannot be the sole sign-off on recorded gate claims.
---

# Context

Parent [[TAS-099-usage-feedback-hardening-round-five]].

Hekate `FBK-006` gap 2 at `0.5.0+gd1a4b82`: the orchestration used a read-only
reviewer agent to independently verify a slice's gates, but that agent has no
shell, so it could not run the gates and its sign-off was necessarily
conditional on the orchestrator rerunning them; it also could not inspect
commit diffs or bodies. Reproduced in
[[THO-014-round-five-usage-feedback-analysis]] by reading the contract:
`SKILL.md` names no verification actor, reviewer, or gate transcript, and its
only verification-boundary text is the node-admission phrase "routine
verification ... never qualify". "Independent verification" therefore depends
on a non-read-only actor for the strongest evidence it claims.

# Outcome

Independent verification of a slice always rests on falsifiable evidence: the
verifying actor can execute the gates, or the handoff carries a coordinator-run
gate transcript, so a no-shell reviewer cannot be the sole sign-off on a
recorded gate claim.

# Done when

- `SKILL.md` states that independent slice verification requires a verifying actor able to execute the gates, or a coordinator-run gate transcript attached to the handoff.
- `SKILL.md` states that a read-only, no-execution reviewer sign-off alone does not falsify a recorded gate claim.
- A `SKILL.md` contract test pins the stated rule and `make test` passes.

# Result

`SKILL.md`'s parallel worktree contract carries a new verification-evidence
bullet beside the coordinator-integrates and resolution-authority clauses. It
states that independent slice verification rests on falsifiable evidence: a
verifying actor that can execute the gates, or a coordinator-run gate transcript
attached to the handoff. It states the complementary limit — a read-only,
no-execution reviewer sign-off alone does not falsify a recorded gate claim, so
it can never be the sole sign-off — and the remedy: when only such a reviewer is
available, the coordinator reruns the gates and attaches the transcript it
verifies.

Evidence: `tests/test_skill.py::test_skill_verification_evidence_contract` pins
the new text via `_VERIFICATION_EVIDENCE_CONTRACT`. `braintree check nodes` and
`make test` (24 passed in `tests/test_skill.py`; full offline suite green) pass.

Limitations: the rule is stated as contract prose and pinned by substring test
only; nothing in `braintree check` enforces which actor ran a gate, because the
vault records node state and not gate transcripts. No vault node had a pinned
`Depends on [[TAS-102-verification-evidence-contract]]` edge, so the resolution
changes no consumer pin and `context_rev` stays `1`.
