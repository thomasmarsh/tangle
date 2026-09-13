---
context_rev: 1
priority: P2
updated: 2026-09-12T16:06:00Z
summary: Add advisory `braintree next --rank` and clustering so frontier selection and hub grouping are direct answers.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

The frontier answers "what is unfinished" but not "what should one actor take
next" or "which candidates belong to the same workstream." Those are graph and
lexical computations over data the sidecar already holds.

# Outcome

`braintree next --rank` orders frontier candidates by priority, transitive
blocking power, and recency, and `frontier --group` clusters candidates by
shared parent, area, and dependencies so a coordinator can assign disjoint
write sets. Both are advisory, never claims.

# Done when

- Ranking is deterministic and documented, with no model required.
- Grouping is advisory and bounded, and its output never becomes authority.
- Tests cover the ranking order and a two-workstream grouping.
- `make test` passes.

# Result

`braintree next --rank` ranks the frontier and `braintree frontier --group`
clusters it, both derived from Markdown alone in `src/braintree/index.py` over
the reverse canonical context edges `braintree impact` already uses, so a
blocking count cannot disagree with the reported impact.

The ranking key is total and model-free, most significant first: `priority`
from `P0` to `P3` with an unset priority last; the transitive blocking count
(unfinished dependents reachable over canonical context edges) descending;
`updated` descending; and the node id ascending. `next --rank [--limit N]`
prints the key in a `ranking` field, bounds the rows, and keeps the unbounded
count in `total`; the default limit is 5.

`frontier --group [--limit N]` joins two frontier candidates into one group
when they share a resolved primary `Parent`/`Area` route or when one depends on
the other through a canonical context edge, merging the connections
transitively. A group is labelled by its shared route, or by its top-ranked
member when the routes differ; rows stay in group-then-rank order and are
bounded, and an explicit `advisory` line states that a group is never a claim
or assignment. The default limit is 10.

Evidence: `tests/test_bt_index.py` covers the priority, blocking, and recency
ordering; the default bounded shortlist; the zero case; two shared-route
workstreams; a dependency-merged group; and the bounded and zero group output;
`tests/test_bt_foundation.py` covers dispatch and argument errors. `make test`
and `make verb-benchmark` pass. `benchmark/verb-baseline.json` is unchanged
because the gated default `frontier` answer is byte-identical; `next` is not
yet a gated case.
