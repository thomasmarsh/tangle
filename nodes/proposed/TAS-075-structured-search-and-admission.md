---
context_rev: 1
priority: P2
updated: 2026-09-12T15:09:27Z
summary: Add structured `braintree search` filters and a near-duplicate `braintree similar` helper for the admission decision.
next: Add status, type, priority, parent, and dependency filters to `search` and a nearest-node `similar` query.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

`braintree search` returns only `id`, `status`, and `summary`, so a client
over-fetches and then filters by reading nodes. The admission rule says to
prefer updating an existing node, but nothing answers "is this already in the
graph?" before a duplicate is written.

# Outcome

`braintree search` accepts structured filters, and `braintree similar` ranks the
nearest existing nodes to a summary or file so the admission decision is made
before a new node is created.

# Done when

- `search` supports status, type, priority, parent, and dependency filters.
- `similar` returns bounded ranked candidates with a stable lexical baseline.
- Tests cover filtered search and a near-duplicate pair.
- `make test` passes.
