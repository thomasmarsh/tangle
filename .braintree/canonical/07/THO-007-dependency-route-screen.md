---
status: resolved
context_rev: 2
updated: 2026-09-14T23:40:13Z
summary: "Reject the dependency-route screen: its fresh composite baseline was rejected before execution by an invalid output schema."
---

# Context

Area [[IDX-001-execution-graph]].

# Result

`token-orientation-baseline-v1.json` is not reusable: its composite fixture
hash is `7214f359…`, while the current zero-call fixture is `6c5cf852…`.
The current skill hash, requested model, and effort match, but the fixture
does not, so a fresh paired baseline was required.

The fresh composite baseline at turn `01a08e45-aa25-70c3-9f92-bcd7c528ef68`
was rejected by the API before model execution: its response schema omitted
`current_decision` from `required`. It has no answer artifact,
`turn.completed`, or token-usage record, so it is invalid and unrecoverable.

The current schema emits every composite property in `required`; the
zero-live test now guards that invariant. Do not run the dependency-route
candidate alone. Its only valid continuation would be a new accepted,
same-fixture baseline/candidate pair, which is not worth the model-token cost
without a separately justified candidate change.
