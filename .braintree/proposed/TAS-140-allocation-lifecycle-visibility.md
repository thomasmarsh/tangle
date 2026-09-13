---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: Document that allocate burns an id and expose outstanding reservations so an unused id is distinguishable from a missing node.
next: Document the allocation burn and expose outstanding reservations so an unused id is distinguishable from a missing node.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-018` finding 2 and Tangle `FBK-025` finding 2 at
`0.6.0+g3bacaf5`. Probe in `/tmp/bt-r7`: `braintree status` prints only
`reservations[1]{prefix,next}` (`TAS,4`), so an id reserved and never written is
invisible; a real groom reported `braintree allocate TAS` returning `TAS-057`
after `TAS-052` with `TAS-053`-`TAS-056` neither nodes nor listed reservations.
The contract never states that an allocation the caller discards is burned
permanently.

# Outcome

The contract states that `braintree allocate` permanently burns an id when the
caller discards it, and a read-only answer lets a groomer tell a
reserved-but-unwritten id from a missing node; an unused allocation can be
released or reclaimed under a stated rule.

# Done when

- Documentation states the burn-and-discard semantics of `braintree allocate`.
- A read-only command or output field lists outstanding reservations or
  otherwise distinguishes burned ids from missing nodes.
- Releasing or reclaiming an unused allocation is either supported with a rule
  or explicitly disposed with rationale.
- Tests cover the visibility answer.
- `make test` passes.
