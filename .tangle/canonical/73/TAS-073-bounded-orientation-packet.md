---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Add a bounded `tangle orient` packet that answers focus, frontier, blockers, stale pins, recent, and conflicts in one call.
---

# Context

Parent [[TAS-068-direct-answer-surface]].

A cold session today reads `SKILL.md`, then `index-map.md`, then runs several
recipes before it can act. The orientation questions are fixed and bounded, so
one command with section flags can replace the pass.

- Builds on the direct answers from [[TAS-071-frontier-and-node-verbs]] and
  [[TAS-072-transitive-dependency-impact]].

# Outcome

`tangle orient` prints one bounded packet with focus, frontier, blockers,
stale pins, recent nodes, and open graph conflicts, section-scoped with a
default limit so it never dumps the corpus.

# Done when

- Each section is independently selectable and bounded.
- The packet is derived only from Markdown plus the rebuildable sidecar.
- Tests cover an empty vault, a single-node vault, and a vault with every
  section populated.
- `make test` passes.

# Result

`tangle orient [--section NAME] [--limit N]` prints one bounded packet with
`focus`, `frontier`, `blockers`, `stale`, `recent`, and `conflicts` sections.
`src/tangle/index.py` derives every section from Markdown alone: focus is the
advisory `# Focus` pointer list in `index-map.md` with each target's status,
frontier and stale reuse the shared derivations, blockers are the blocked
nodes, recent is ordered by `updated`, and conflicts is
the checker's own `graph_check.findings` so the packet cannot disagree with
`tangle check`. Each section is independently selectable with a repeatable
`--section`, printed in canonical order, and truncated to `--limit` (default
`10`) while a `total` field keeps the unbounded count, so one call never dumps
the corpus.

Evidence: `tests/test_tangle_index.py` covers a vault with every section populated,
an empty vault, a single-node vault, a missing nodes directory, selectability
and the per-section limit versus total, and ties the conflicts rows to
`tangle check --format toon`; `tests/test_tangle_foundation.py` covers dispatch
and the argument errors. `make test` passes.
