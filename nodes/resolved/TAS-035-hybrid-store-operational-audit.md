---
context_rev: 1
priority: P2
updated: 2026-09-11T22:18:40Z
summary: Audit confirms Markdown authority, external sidecar isolation, recovery, and same-host coordination boundaries.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

# Result

`scripts/bt` is the sole command boundary: Markdown retains prose, links, pins,
status, priority, and `next`; SQLite holds only rebuildable index/FTS rows and
local claims/allocation. `bt reindex` rebuilds after database loss, while
`bt init` repairs the operational sidecar. No database, WAL, or SHM path is
tracked; `.gitignore` also excludes their in-repository forms.

`tests/bt-foundation.sh`, `tests/bt-index.sh`, and `tests/bt-verification.sh`
pass. The verification test proves non-mutating reindex/search/backlinks/stale,
recovery after deleting the test database, shared Git-common-dir identity and
claim visibility across worktrees, and network-filesystem refusal. It also
proves competing claims and allocations serialize correctly. `graph-check` and
`git diff --check` pass.

The live default sidecar resolves outside the repository at
`~/.local/state/braintree/projects/732e1b1cf1dbb6f3891f/graph.sqlite3`, with zero
claims. This sandbox permits reading it but rejects reindex writes, so its live
write path was not altered; disposable local sidecars supplied the write and
recovery evidence. This is an environment restriction, not durable graph state.

No measured remaining status-rename or metadata-conflict churn justifies a
stationary-path or database-owned status migration. Keep that deferred under
[[TAS-036-stationary-path-migration-evaluation]].
