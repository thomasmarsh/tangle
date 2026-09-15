---
status: active
context_rev: 3
priority: P0
updated: 2026-09-15T00:01:37Z
summary: Implement stable lowercase node and project identity.
next: Reconcile the skill contract text and references with the stationary canonical store and compatibility window.
---

Parent [[TAS-193-same-directory-graph-contribution-intake]].

# Context

Depends on [[DEF-003-opt-in-change-intake-protocol-v1]] at context_rev 4.

This task separates logical identity, project authority, canonical location, content revision, and presentation before proposal encoding depends on any of them. Existing uppercase numeric nodes are legacy inputs, not a reason to preserve centralized numeric allocation for new nodes.

Gates my artifacts enter: `tests/test_scaffold.py` and `tests/install.sh` for packaged source or reference files, `tests/test_skill.py` for contract text, the graph and vault tests for format discovery, and the default ruff, mypy, and pytest discovery over new modules.

# Outcome

Every newly admitted node has a lowercase globally collision-resistant identity and a stable canonical path under a clone-stable project UID, while existing vaults and uppercase numeric references remain readable through an explicit migration and compatibility contract.

# Done when

- A cryptographically random immutable project UID is committed with the vault and shared by clones. It uses a `prj-` prefix plus exactly 128 bits encoded as 26 lowercase Crockford Base32 characters, for example `prj-04r8b1t7n2c6m9x3q5f0hkwdza`, and is explicitly distinct from the existing Git-common-directory hash used to locate same-host sidecar state.
- Lowercase project aliases use a conservative ASCII grammar, live in presentation or local registry state, and never confer authority. CLI input accepts `tas-...` locally and `tangle:tas-...` as a qualified convenience spelling, then resolves the latter to the committed project UID.
- New `tas`, `tho`, `def`, `dec`, `idx`, and `fbk` IDs use their lowercase type prefix plus exactly 128 bits encoded as 26 lowercase Crockford Base32 characters, for example `tas-01k5v6m3x8f2q7c9d4hn8w2pza`. The canonical payload grammar is `[0-7][0-9a-hjkmnp-tv-z]{25}`; generation happens only at admission from cryptographic entropy or the versioned domain-separated digest construction. Proposal-local symbols remain noncanonical, content hashes remain revision witnesses, and no shared numeric sequence is needed for new identities.
- Newly stored identifiers, filenames, project aliases, and qualified reference components use lowercase ASCII. Input normalization and duplicate checks cannot let differently cased spellings become distinct on a case-sensitive filesystem or alias on a case-insensitive one.
- Human terminal views may display a collision-aware abbreviation such as `tas-01k5v6m3...`, using at least eight payload characters and deterministically lengthening until unique in the rendered result set. The ellipsis is mandatory, a full-width mode remains available, and canonical Markdown, filenames, links, protocol artifacts, durable evidence, and structured or machine-readable output always use the full ID. Abbreviations are never accepted or persisted as identity and require no client-maintained mapping.
- Canonical nodes occupy one stable, optionally sharded path derived from immutable identity, with an immutable creation label only if the format retains one for readability. Status becomes an authoritative node field rather than part of the path.
- Same-project graph edges remain valid Obsidian wikilinks. Cross-project edges use a distinct durable Braintree reference or URI containing the immutable project UID; a colon-qualified shorthand is never stored as though it were a local wikilink. Missing project registration preserves a visible unresolved external edge.
- Legacy uppercase numeric IDs, basenames, wikilinks, and status-directory nodes remain readable during a versioned compatibility window. Migration is one-way, collision-checked, recoverable, and uses an intermediate path for case-only renames. It preserves Git history as far as Git can detect and rewrites canonical backlinks coherently.
- The stationary-storage benchmark is rerun under the derived-index architecture and measures stable paths, status transitions, direct point edits, sidecar loss, Obsidian navigation, case behavior, and optional symlink views. The selected layout and rejected alternatives are recorded with rollback evidence.
- Tests cover exact 128-bit encoding and rejection of noncanonical payloads, clone-stable project identity, alias collision and rename, local and qualified resolution, full-width output, collision-aware abbreviation lengthening, ID collision injection, content edits without identity changes, case-insensitive equivalence, mixed legacy/new vaults, interrupted migration, and round-trip Markdown preservation. `braintree check`, `make test`, and the storage benchmark gate pass.

# Result

Completed the identity foundation slice: `identity.py` now generates and
validates exact lowercase 128-bit Crockford IDs and committed `prj-` UIDs,
normalizes canonical-ID input without accepting abbreviations, resolves
alias-qualified input to immutable project authority, and produces
collision-aware terminal abbreviations. Added this vault's committed
`project-id`; `braintree location` reports it separately from the legacy
Git-common-directory sidecar key. Focused identity, CLI, lint, and type checks
pass. `make test` reached 791 passing tests but retains the pre-existing
`test_memory_authority` frozen-artifact derivation failure; no benchmark
artifact was changed. Remaining: switch writers and readers to the stationary
canonical store, then implement the compatibility migration and storage
benchmark evidence.

Completed the compatibility-reader slice: `store.py` centrally discovers both
legacy status-directory nodes and stationary canonical nodes, whose `status`
frontmatter is authoritative. Graph validation, indexing, frontier discovery,
decomposition lookup, and feedback scans now share that discovery contract;
mixed-layout stationary fixtures pass their graph and index checks. Remaining:
write canonical nodes into the stationary layout, implement the collision-safe
explicit migration, and record the storage benchmark evidence.

Completed the stationary-writer slice: node capture, feedback capture, and
decomposition now create lowercase 128-bit IDs from cryptographic entropy and
write each node once under `canonical/<payload-suffix>/`, with authoritative
frontmatter status. Writers ensure a clone-stable project UID without numerical
sidecar allocation; concurrent UID creation tolerates the publication race.
Updated capture, index-upkeep, decomposition, installer, and sidecar-boundary
tests to assert canonical identities while preserving legacy-reader fixtures.
Remaining: implement the collision-safe explicit migration and record the
storage benchmark evidence.

Completed the explicit compatibility-migration slice: `migration.py` and
`braintree stationarize [NODES] [--apply]` plan every legacy status-directory
node's move to `canonical/<suffix>/` and reject the whole vault before writing
anything on a duplicate identity or an occupied target. Apply preserves
identity, basename, and wikilinks, so Git still records a rename and no
consumer reference changes; it adds the authoritative `status` field, refreshes
only `updated`, and leaves `context_rev` unchanged because the node's meaning is
unchanged. A failed apply restores every journalled source byte-for-byte, a
case-only rename is staged through an intermediate name, and the verb plans by
default so a dry run writes nothing. Made `tests/test_bt_index.py` derive the
live frontier through the shared authority-bearing file set instead of a
status-directory glob, which the stationary layout had invalidated. New
migration tests, `ruff`, and `mypy` pass; `uv run pytest` is green except the
pre-existing `test_memory_authority` frozen-artifact derivation failure
(confirmed failing before this change). Remaining: rerun and record the
stationary-storage benchmark under the derived-index architecture and its layout
and rollback evidence.

Applied the migration to this vault by owner authorization: 245 legacy nodes
moved into `canonical/<suffix>/` with an authoritative `status` field, and
`braintree check` passes at 251 nodes. Making the live vault stationary exposed
storage-layout assumptions, so added `store.find_by_name` and routed the
memory-harness observable resolver, the corpus citation check, and the
authority path check through it, and made the live-vault skill tests and the
`indexmap.md` recipes derive from the authoritative status field instead of a
status-directory glob. `ruff`, `mypy`, the install and worktree shell suites,
and `uv run pytest` pass except the same pre-existing `test_memory_authority`
frozen-artifact failure. Remaining: record the stationary-storage benchmark
evidence, and reconcile the skill contract text, which still describes status
directories as the only layout now that writers and this vault use the
stationary store.

Recorded the derived-index storage comparison: `storage_comparison.py` now also
measures a direct in-place point edit, status-authority survival after
derived-state loss, basename-wikilink stability across a status transition,
case-only rename staging, and whether a symlink view is a second authority,
alongside the existing transition, query, conflict, stale-view, and stable-path
columns. The rerun shows a stable path and an `M`/1 point edit in every layout
(identity is layout-independent); stationary is the only layout that combines a
stable path with status authority that survives derived-state loss, directory
authority pays a rename for every status transition, and the symlink and copied
index layouts lose the active set when their derived view or cache is removed.
Updated `benchmark/storage-comparison-baseline.txt`, rewrote the BENCHMARK.md
section to select stationary canonical storage and reject the directory,
symlink-view, and copied-index alternatives with derived-state-loss recovery,
one-way collision-checked migration, and byte-for-byte apply rollback as the
rollback evidence, and added the case-only-rename contract test. `braintree
benchmark storage --verify`, `ruff`, `mypy`, and `braintree check` (251 nodes)
pass; `make test` passes 815 with the same pre-existing `test_memory_authority`
frozen-artifact failure. Remaining: reconcile the skill contract text and
references, which still present status directories as the only layout.
