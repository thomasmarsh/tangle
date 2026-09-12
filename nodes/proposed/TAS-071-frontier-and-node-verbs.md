---
context_rev: 1
priority: P1
updated: 2026-09-12T15:09:27Z
summary: Add `braintree frontier` and `braintree node` so the current frontier and a node's graph view are direct CLI answers.
next: Implement `braintree frontier` and a normalized `braintree node ID` view over the derived index.
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
