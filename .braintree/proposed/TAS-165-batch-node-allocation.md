---
context_rev: 1
priority: P2
updated: 2026-09-14T00:18:39Z
summary: Let braintree allocate atomically reserve a caller-requested count of consecutive ids in one call.
next: Add an optional count operand to braintree allocate and its sidecar reservation primitive.
---

# Context

Area [[IDX-001-execution-graph]].

`braintree allocate PREFIX` reserves exactly one id per invocation, so a caller
that needs several ids — a coordinator preallocating for parallel workers, or a
scenario minting a small batch of nodes — must either invoke it once per id or
fall back to a hand-picked range and reconcile it afterwards. [[TAS-023-parallel-id-allocation]]
established the atomic reservation primitive, [[TAS-103-make-one-command-node-capture-preserve-atomic-id]]
reused it for the record paths, and [[TAS-140-allocation-lifecycle-visibility]]
documented the burn-and-discard rule; none of them lets one call reserve more
than one id.

# Outcome

`braintree allocate PREFIX` accepts an optional positive count and atomically
reserves that many consecutive ids, reporting the reserved ids under the same
burn-and-discard rule as a single allocation, while the one-count invocation
keeps its current output.

# Done when

- `braintree allocate PREFIX [COUNT]` reserves `COUNT` consecutive ids in one
  atomic call, and the count defaults to one.
- The reserved ids are reported in a stable, parseable form.
- A non-positive or malformed count is a usage error (exit 2) that reserves
  nothing.
- Concurrency and burn semantics stay identical to the single-id path.
- `braintree allocate --help`, `references/coordination.md`, and the command
  index describe the count operand.
- `make test` and `braintree check` pass.
