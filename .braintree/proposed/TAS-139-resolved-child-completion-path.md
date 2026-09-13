---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: Define the worker-side completion path and checker distinction for a resolved child whose parent next has not advanced.
next: State the worker-side completion and handoff path and separate the multi-writer transient from a genuine stale route.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-017` and `FBK-023` finding 3 at `0.6.0+g3bacaf5`. Round six
[[TAS-115-parent-next-advance-ownership]] already made `braintree check` report a
stale route as `next-resolved-node` and stated that the coordinator owns the
advance when the worker's write set excludes the parent. The unhandled residual
is that the worker is left between a red gate and an out-of-write-set edit with
no stated completion rule, the failure appears the moment the file moves (before
any commit), and the checker cannot distinguish the normal multi-writer handoff
transient from a genuine stale route. Tangle `FBK-023` finding 3 adds that the
parent-next advance should fold into the resolving worker's commit whenever the
write set names the parent, to remove a coordinator round trip.

# Outcome

The contract states what a frontier-child worker commits and hands off while the
parent's `next` still names the resolved child and how the coordinator restores
the plain gate, folding the parent advance into the resolving worker's commit
when its write set names the parent; the checker separates that transient handoff
state from a genuine stale route.

# Done when

- `SKILL.md` or `references/coordination.md` states the worker-side completion
  and handoff for this case.
- The checker's `next-resolved-node` diagnostic or a documented transient rule
  distinguishes the multi-writer transient from a genuine stale route.
- Folding the parent advance into the resolving worker's commit when the write
  set names the parent is stated and tested.
- Tests cover the transient and the genuine stale route.
- `braintree check` and `make test` pass.
