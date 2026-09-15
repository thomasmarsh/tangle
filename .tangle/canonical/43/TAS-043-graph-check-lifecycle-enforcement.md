---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: graph-check now rejects the blocked-section, disposition, and task-next lifecycle violations its contract documents.
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[TAS-014-graph-validator]] at context_rev 1.

# Outcome

`graph-check` rejects the lifecycle violations its contract already documents: a
proposed or active task without `next` regardless of ID prefix, a blocked node
without a `# Blocked` section naming `Blocked by` and `Unblocks when`, and a
`disposition` value outside `abandoned`/`deprecated`/`superseded` or attached to
a non-resolved node.

# Done when

New negative fixtures fail with clear errors while the real vault and the valid
fixture still pass, through both the pytest suite and `tests/graph-check.sh`.

# Result

Before this change the validator passed four fixture violations:
`BUG-001` active without `next`, a blocked node without a `# Blocked` section,
`disposition: current`, and `disposition` on an active node. `graph_check.py`
now derives the node type from the ID and requires `next` for every
non-knowledge task type (`THO`/`DEF`/`DEC`/`IDX` are exempt), requires a
`# Blocked` section containing both `Blocked by` and `Unblocks when`, and
enforces the disposition enum on resolved nodes only. The cold-resume token
fixture's blocked distractor node now carries a conforming `# Blocked` section.

Evidence: five new pytest cases in `tests/test_graph_check.py`, three new
`tests/graph-check.sh` cases, and the empty restore of the shell fixture's
parent-cycle mutation. `make test` passes (74 pytest tests, ruff, strict mypy,
and every shell suite), and `graph-check nodes` passes on the real 54-node vault.
