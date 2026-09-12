---
context_rev: 1
priority: P1
updated: 2026-09-12T15:09:27Z
summary: Give check, index, and stale one canonical context-edge definition and one unresolved-pin answer.
next: Define the canonical context-edge set once and route check, index, and stale through it.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

This is the lowest-risk child because the tooling currently contradicts itself.
`braintree check` treats `Implements`, `Requires`, and `Governed by` as context
edges, while `braintree stale` filters to `Depends on` alone, and `stale` does
not report a pinned target that is not resolved even though `check` now does. A
node can therefore pass `braintree stale` and fail `braintree check`.

# Outcome

`check`, the derived index, and `stale` share one context-edge definition, and
`stale` reports a pinned target that is missing, revision-mismatched, or not
resolved.

# Done when

- One canonical context-edge set is defined and used by the validator and the
  derived index.
- `braintree stale` reports an unresolved pinned target with the same verdict as
  `braintree check`.
- Regression tests cover a pin on each context relation and an unresolved pin.
- `make test` passes.
