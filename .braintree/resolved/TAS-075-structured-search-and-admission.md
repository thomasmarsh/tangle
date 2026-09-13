---
context_rev: 1
priority: P2
updated: 2026-09-12T16:01:14Z
summary: Add structured `braintree search` filters and a near-duplicate `braintree similar` helper for the admission decision.
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

# Result

`braintree search QUERY [--limit N]` now accepts five structured filters. Each
flag takes one value and the set combines with AND; status, type, and priority
are case-normalized and validated (status against the four directories, priority
against `P0`-`P3`, type as an uppercase node-type prefix). The filter data is
derived from the authoritative Markdown, not from a sidecar column: `--status`
matches the status directory, `--type` the ID prefix, `--priority` the
frontmatter priority, `--parent` the primary `Parent`/`Area` route (a bare ID or
a full name), and `--dependency` any canonical context edge. The full-text
engine is unchanged: the sidecar's FTS still ranks the matches and
`index.search` applies the Markdown-derived predicate before `limit`, so a
filtered search cannot drop below its limit. `similar TEXT|--file PATH
[--limit N]` ranks existing nodes by cosine similarity over the lowercased
alphanumeric token counts of the input and each node's `summary` plus body, only
returning positive scores and breaking ties by node ID. It is deterministic and
model-free, the stable lexical baseline the admission decision compares a draft
against; the optional semantic layer of [[TAS-079-optional-semantic-retrieval]]
may rerank it without changing this path.

Evidence: `tests/test_bt_index.py` covers each filter, a combined and a
zero-result case, invalid filter arguments, the near-duplicate pair, a bounded
limit, a zero-candidate query, and `--file`; `tests/test_bt_foundation.py`
covers dispatch and argument errors. `uv run braintree check nodes` passes (97
nodes), `make verb-benchmark` passes unchanged (the gated verbs' output is
untouched), and `make test` passes (236 passed).
