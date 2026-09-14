---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Maintain the derived index automatically on every interaction and stop naming SQLite or the sidecar as a client concept.
---

# Context

Parent [[TAS-161-routine-interaction-zero-ceremony]].

`references/coordination.md` opens with a "Hybrid sidecar contract" that teaches
clients to run `braintree index`, to run `braintree init` before coordinated
work, to recover with `braintree init` then `braintree index`, and to reason
about SQLite/WAL, `BT_SIDECAR_DIR`/`BT_PROJECT_ID`, and network-mounted
locations. `references/authoring.md` and `SKILL.md` also name the sidecar. The
sidecar is derived, disposable coordination state; a client should neither have
to know it exists nor keep it current by hand. Automatic maintenance is the
prerequisite that makes removing it from the client contract truthful, so the two
land together.

# Outcome

Interactions maintain the derived index automatically and incrementally,
`braintree index` survives only as an explicit repair or rebuild, and `SKILL.md`
and `references/` no longer present SQLite, the sidecar, or an index-update step
as a client-managed concept; they state only the markdown-authoritative behavior
and concurrency guarantees a client relies on.

# Done when

- Mutating and direct-answer interactions keep the derived index current without
  a separate client step.
- `braintree index` remains available only as repair or rebuild, and its help
  says so.
- `SKILL.md` and `references/` no longer name SQLite or the sidecar as a client
  concept, while the markdown authority and concurrency guarantees remain stated.
- Rebuilding the index from Markdown alone recovers after its loss.
- Tests cover automatic maintenance and the rebuild-from-markdown recovery.
- `make test` passes.

# Result

Index upkeep now triggers after every dispatched interaction except `init`,
`index`, `migrate`, and `check`, and only when the project's local coordination
state already exists, so a read-only answer still creates no state. Scope is the
resolved vault (`BT_NODES_DIR` or `./.braintree`) and the derived node, edge, and
full-text rows for it. An absent state file, an unresolvable state location, and
a concurrent writer's lock are silent no-ops; any other upkeep failure is one
warning on stderr — the channel the orphan pre-check already uses — and never
changes the answer or the exit code.

`src/braintree/main.py` splits dispatch from `main` and calls the new
`index.refresh`; `src/braintree/index.py` adds it beside the whole-rebuild
`index.reindex`. `refresh` reads the Markdown snapshot, compares it with the
indexed rows, and writes only the changed node rows, the added or removed edge
rows, and the deletions: an unchanged vault opens no write transaction, and every
write is a conflict-tolerant upsert, so concurrent upkeep converges rather than
failing on a duplicate identity (the failure that an eight-way concurrent
allocation probe first exposed). `braintree index` keeps `reindex` and is now
documented as repair-or-rebuild only in `SKILL.md`, `references/coordination.md`,
and `braintree index --help`.

`references/coordination.md` replaces "Hybrid sidecar contract" with a "Local
coordination contract" stating the Markdown authority, the disposable derived
state, the self-maintaining index, and the same-host concurrency guarantee;
`SKILL.md`, `references/authoring.md`, and the printed `help.py` strings no longer
name SQLite, a sidecar, its environment overrides, a network-mounted location, or
a manual `braintree init`/`braintree index` step.

Evidence: `tests/test_index_upkeep.py` (11 cases) pins that a read-only and a
mutating interaction keep the index current with no client step, that incremental
upkeep equals a full rebuild, that an unchanged vault rewrites no indexed row,
that emptied rows and a lost state file are recovered from Markdown alone, that a
deleted node takes its rows and edges with it, that a read-only interaction
creates no state, and that a broken index or an unreadable node warns without
failing the interaction. `tests/test_skill.py` adds the `braintree index --help`
repair/rebuild pin, the core and reference upkeep pins, and a negative-assertion
guard with a falsification probe that no installed surface names the local state.

Gates: `braintree check` passed (197 nodes); `braintree benchmark verbs --verify`
passed; `make test` passed (719 passed, 3 skipped). No benchmark artifact was
regenerated and the seven prompt-observable source files are unchanged.

Limitations: `braintree search`, `braintree backlinks`, and `braintree stale`
still call the whole-rebuild `index.reindex` inside `cli.py`, which this slice may
not edit, so those three verbs keep paying a full rebuild before they answer; the
automatic upkeep is what makes the index current for every other interaction.
`README.md` still describes the local sidecar and a manual `braintree init`/
`braintree index` recovery, which this node's Done when does not name.
