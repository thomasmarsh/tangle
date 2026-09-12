---
context_rev: 1
updated: 2026-09-12T23:37:51Z
summary: Make one-command node capture preserve atomic ID allocation under parallel callers.
next: Add a concurrent capture test with different slugs that attempts to reserve the same numeric ID.
---

Area [[IDX-001-execution-graph]].

# Context

`braintree node record` and `braintree feedback record` derive the next ID from Markdown and use an exclusive create on the full filename. Two parallel callers with different slugs can therefore create distinct files with the same numeric ID. This bypasses the sidecar allocation rule established by [[TAS-023-parallel-id-allocation]].

# Outcome

The one-command record paths either reserve their automatically chosen IDs atomically or require and clearly document an ID preallocated with `braintree allocate` whenever concurrent creation is possible.

# Done when

- A concurrent different-slug regression test cannot create duplicate numeric IDs.
- `node record` and `feedback record` share one stated allocation contract.
- The portable no-sidecar path remains explicit if atomic allocation is unavailable.
- `make test` passes.
