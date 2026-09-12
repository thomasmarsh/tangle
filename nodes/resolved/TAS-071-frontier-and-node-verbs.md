---
context_rev: 1
priority: P1
updated: 2026-09-12T15:34:00Z
summary: Add `braintree frontier` and `braintree node` so the current frontier and a node's graph view are direct CLI answers.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

The frontier is currently the `Frontier` shell recipe in `nodes/index-map.md`,
and a node's graph view requires `find`, opening the file, and a separate
`braintree backlinks` call. Both are direct questions the sidecar already has
the data to answer.

# Outcome

`braintree frontier` lists the unfinished nodes whose `next` is an action, with
identity, status, priority, summary, `next`, and a stale flag. `braintree node
ID` prints frontmatter, primary route, context edges with pin versus current
revision, and backlinks.

# Done when

- The frontier verb matches the Markdown-derived frontier on the live vault and
  on a temporary fixture.
- The node verb resolves a bare ID or full name and reports the graph view.
- Tests tie both answers to the Markdown derivation.
- `make test` passes.

# Result

`src/braintree/index.py` derives both answers from Markdown alone, so
`braintree frontier` and `braintree node ID` need no sidecar and cannot drift
from the vault. `frontier` follows the documented recipe: the unfinished nodes
whose `next` is an action rather than a single child route, reporting identity,
status, priority, summary, `next`, and a stale flag from the shared
`context_pin_problem` verdict. `node` resolves a bare ID or full node name and
prints frontmatter, the primary `Parent`/`Area` route, context edges with pin
versus current revision, and backlinks.

`tests/test_bt_index.py` ties the frontier set and the node view to an
independent Markdown derivation on the live vault and on a temporary fixture;
`tests/test_bt_foundation.py` covers dispatch and argument errors. `make test`
passes.
