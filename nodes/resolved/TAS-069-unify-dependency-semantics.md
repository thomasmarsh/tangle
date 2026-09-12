---
context_rev: 1
priority: P1
updated: 2026-09-12T15:22:06Z
summary: Unified check, index, and stale on one canonical context-edge set; stale now reports missing, revision-mismatched, and unresolved pins.
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

# Result

`CONTEXT_RELATIONS` (`Depends on`, `Implements`, `Requires`, `Governed by`) is
now the single context-edge set. It is defined once in
`src/braintree/graph_check.py`, drives that module's `_check_context_edges`, and
is imported by `src/braintree/index.py`, where `stale` filters edges with it.
The shared `context_pin_problem`/`stale_reason` verdict answers unpinned,
missing target, unresolved target, and revision mismatch, so `check` and `stale`
reach the same conclusion from one predicate instead of two independent rules.

`braintree stale` gained `relation` and `reason` columns and now reports a
pinned target whose status is not `resolved`; its reason shares the `check`
verdict wording. The canonical set lives in `graph_check` rather than a new
package module because the composite token-benchmark fixture pins a hardcoded
file count in `tests/test_token_benchmark.py`, which is outside this node's
write set; a new `src/braintree/*.py` file would have failed that test.

Evidence:

- `CONTEXT_RELATIONS`, `context_pin_problem`, and `stale_reason` in
  `src/braintree/graph_check.py`; `_check_context_edges` consumes the first two.
- `index.stale` in `src/braintree/index.py` selects `e.relation IN
  CONTEXT_RELATIONS` and filters with `context_pin_problem`.
- `cli._stale` in `src/braintree/cli.py` prints the `relation` and `reason`
  columns.
- `test_each_context_relation_requires_a_pin` in `tests/test_graph_check.py`
  covers a pin on each canonical relation in the validator.
- `test_stale_reports_each_context_relation`, `test_stale_reports_missing_pinned_target`,
  and `test_stale_and_check_agree_on_unresolved_pin` in `tests/test_bt_index.py`
  cover each relation, a missing target, and the unresolved-pin agreement with
  `check`.
- `make test` passes (147 tests).
