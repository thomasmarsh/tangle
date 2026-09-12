---
context_rev: 1
priority: P1
updated: 2026-09-12T16:40:00Z
summary: Make the frontier answers name the coordinator's deliberate frontier child instead of every action-next proposed sibling, and state the plan-text gate status.
next: Decide whether the verbs derive the coordinator's frontier or the contract states they return a candidate list.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N2: `braintree frontier`, `braintree next --rank`, and `braintree orient`
report every unfinished node whose `next` is an action. For a user-requested
plan whose children are created up front as `proposed`, the coordinator's
sequenced-but-not-frontier siblings therefore appear as equal candidates even
though the contract calls them "not yet at the frontier". N3: the contract also
does not state which status a gate on un-tracked plan text takes.

# Outcome

The frontier answers and the contract agree on the one deliberate frontier
child, and a plan-text gate has a stated status.

# Done when

- `braintree frontier`, `next`, and `orient` either return the coordinator's `next` target as the frontier or the contract states the answer is a candidate list that a worker must resolve through the coordinator.
- The `blocked` versus `proposed` guidance covers a gate on prerequisite plan text that no node owns.
- A vault fixture with an up-front plan and sequenced siblings has regression tests for the chosen behavior.
- `make test` passes.
