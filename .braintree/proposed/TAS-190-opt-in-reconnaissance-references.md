---
context_rev: 1
updated: 2026-09-14T13:39:17Z
summary: Add opt-in references from work nodes to shared reconnaissance.
next: Define the relation syntax and falsifying graph cases.
---

Parent [[TAS-189-usage-feedback-hardening-round-eleven]].

# Context

Tangle `FBK-032` finding 5 identifies two separate concerns. The load-band and size-command concern remains owned by [[THO-024-whether-node-files-need-a-bounded-load-band-with]]. This node owns only the missing capability for a work node to cite reusable `THO` reconnaissance without turning that context into a pinned dependency or copying it into every task.

Tangle `THO-014`, `THO-015`, and `THO-016` demonstrate the desired producer shape: durable reconnaissance routed to the Tangle hub and consumed selectively by later work. The Braintree contract currently defines primary routes, pinned `Depends on`, unresolved `Gated on`, and supersession, but no canonical non-pinned context-reference edge or read expansion for it.

# Outcome

Authors can link optional shared reconnaissance through one canonical relation, and readers can request a bounded orientation packet that includes those references without changing readiness, reachability, or `context_rev` semantics.

# Done when

- The contract defines one canonical relation from a consuming work node to a referenced knowledge node, including allowed target types, direction, multiplicity, and placement.
- The relation is explicitly non-pinned and does not imply readiness, staleness, primary routing, ownership, or automatic context loading.
- `braintree check` validates malformed or invalid uses structurally without claiming semantic authority over whether the context is useful.
- A supported `braintree node` option or equivalent read surface returns the requested node plus its directly referenced reconnaissance in deterministic, bounded output and documents cycle and missing-target behavior.
- Existing node output remains unchanged unless the opt-in expansion is requested.
- Help, authoring or dependency guidance, and tests cover the consumer-authored shape and negative cases.
- `make test` passes.
