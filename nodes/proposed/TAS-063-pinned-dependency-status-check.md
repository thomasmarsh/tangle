---
context_rev: 1
priority: P2
updated: 2026-09-12T13:58:00Z
summary: Surface a pinned dependency that is not resolved, or explicitly document the knowledge-node exemption, so the manual gate is enforceable.
next: Extend graph-check or bt stale to report a pinned dependency whose target is proposed or blocked, and state when a DEF or DEC is resolved.
---

# Context

Parent [[TAS-058-usage-feedback-hardening-round-two]].

Feedback finding R5 from Tangle `THO-006-braintree-friction-shared-render-layer` F1:
the loop says to confirm a pinned dependency is resolved, but
`graph-check` and `bt stale` both pass a pin whose target is still `proposed`,
and the skill never states when a `DEF`/`DEC` becomes resolved.

# Outcome

A pinned dependency that is not `resolved` is reported by the tooling, or the
skill explicitly exempts knowledge nodes and states the intended ordering; the
skill also states when a settled `DEF`/`DEC` is resolved.

# Done when

- `graph-check` or `bt stale` reports a pinned dependency whose target is `proposed` or `blocked`, or `SKILL.md` documents the exemption and ordering.
- `SKILL.md` states that a settled `DEF`/`DEC` is resolved.
- A regression test covers the reported state.
- `make test` passes.
