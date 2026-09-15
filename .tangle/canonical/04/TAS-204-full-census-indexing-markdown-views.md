---
status: proposed
context_rev: 2
priority: P0
updated: 2026-09-15T00:25:54Z
summary: Implement full-census indexing and generated Markdown views.
next: Reconcile the canonical-store hash census before command dispatch and report it on the diagnostic surface.
---

Parent [[TAS-193-same-directory-graph-contribution-intake]].

# Context

Gated on [[TAS-203-stable-lowercase-node-project-identity]].

Stable storage is usable only if Tangle owns discovery and presentation. No client may be required to maintain hashes, indexes, status pages, summary aliases, external-project proxies, or symlink trees.

Gates my artifacts enter: `tests/test_scaffold.py` and `tests/install.sh` for packaged source or generated-view support, vault and index tests for canonical discovery, `tests/test_skill.py` for the client-responsibility boundary, and default ruff, mypy, and pytest discovery over new modules.

# Outcome

Every Tangle command observes direct canonical-file changes before answering, and Tangle automatically publishes deterministic Markdown navigation views from the same reconciled snapshot without making those views authoritative.

# Done when

- Every project-scoped command entry point that reads or mutates graph state first enumerates the complete canonical node store, excluding proposals, acceptances, receipts, generated views, and temporary files, and reads a cryptographic hash of every node's exact bytes. Mtime, size, inode, watchers, Git status, and caller-supplied paths may be hints but never replace this census; global help, version, installation, and equivalent repository-independent paths do not require a vault.
- One transactional reconciliation compares path, normalized identity, and digest sets; parses new or changed files only; removes vanished rows; detects normalized duplicates; and updates nodes, edges, FTS, status, dependency, reservation, and other derived answers before command dispatch reads them. Sidecar loss performs a full parse.
- Same-directory Tangle commands serialize census, index reconciliation, canonical mutation, and view publication with a project-scoped lease. A direct nonconforming edit detected during the census causes retry or an explicit concurrent-edit result; an edit after the validated boundary is observed by the next command. The implementation does not claim an atomic multi-file snapshot against arbitrary writers.
- A mutating command begins from that reconciled snapshot, applies its canonical mutation, then publishes its known index delta and affected projections before returning; it need not perform a redundant second full census of files it exclusively wrote. A later command still catches any intervening external edit.
- Generated Markdown pages provide at least by-status, by-area, by-priority, recent, and registered-external-project navigation. They render the current canonical summary as link display text and use full stable canonical targets, deterministic ordering, and no volatile timestamp that causes no-op rewrites; collision-aware shortened IDs are reserved for human terminal presentation and never leak into stored links or view authority.
- Views are disposable, untracked or otherwise excluded from canonical authority, ignored by node discovery and graph validation, and rebuilt through immutable generation content plus atomic same-directory file publication or an equivalent generation marker. Missing, mixed-generation, corrupt, or stale views never hide a canonical node. Optional symlink views are a backend, not a correctness dependency.
- A project registry maps lowercase aliases to immutable project UIDs and local vault locations. When an external project is available, Tangle may generate a proxy or hyperlink; when absent, the durable external reference remains unresolved and visible without creating a fake canonical node.
- A dedicated status or diagnostic surface reports whether the last hash census found zero or N changes and whether views were current, updated, or failed. Routine command output remains compatible and silent on successful no-op upkeep; projection failure is explicit and retryable and cannot make a generated page evidence that an unaccepted canonical mutation succeeded.
- Fault tests preserve mtimes while changing bytes, add and delete files between commands, change case, corrupt the sidecar and views, race a direct edit with command startup, interrupt index and view publication, and verify that the next command repairs derived state before answering.
- A scaling benchmark records total bytes hashed, changed files parsed, pages rewritten, and wall time for no-change and point-change runs. Acceptance thresholds keep the universal scan bounded, and `tangle index` remains repair-oriented rather than client bookkeeping.
- `tangle check`, `make test`, and every index, installer, Obsidian, storage, or benchmark gate implicated by the implementation pass.

# Result

Completed the project-owned generated-views slice. `views.py` now builds five
deterministic pages from the canonical store -- by-status, by-area (the `Area`
link, else `Parent`), by-priority, recent, and registered-external-project --
rendering each node's canonical summary as `[[stable-basename|summary]]` link
display text with fixed grouping orders and no generation timestamp, so an
unchanged vault reproduces every page byte for byte and a no-op interaction
rewrites nothing. `publish` stages each changed page in a same-directory
process-unique temporary file and atomically renames it, removes a page the
builder no longer produces, and tolerates a concurrent writer replacing the
same canonical bytes. Automatic upkeep now reconciles the derived index and
publishes the views after every non-excluded interaction; `tangle index`
repairs and republishes them and reports `views`; `tangle status` reports
`views: current (N)`, `stale (N pending)`, `failed`, or `unavailable` without
writing. `store.NON_NODE_DIRECTORIES` excludes `views/` (with the reserved
`proposals/`, `acceptances/`, and `receipts/`) from node discovery and graph
validation, so a generated page is never a node or an invalid-status finding,
and `.gitignore` keeps the disposable pages out of the repository. The new
`tests/test_views.py` covers publication, direct-edit reach, grouping,
byte-for-byte no-op idempotence, discovery exclusion, the `status` stale-to-
current transition, `index` republication, and an external project registry
entry; `tests/test_tangle_verification.py` now asserts the canonical Markdown is
unchanged while excluding the non-authoritative views. `ruff`, `mypy`, and
`uv run pytest` pass except the pre-existing `test_memory_authority`
frozen-artifact derivation failure, and `tangle check` passes at 251 nodes.

Remaining, in order: reconcile the complete canonical-store hash census before
command dispatch and report zero-or-N changes and view state on the diagnostic
surface; replace the per-command full reindex in the sidecar query verbs with
that reconciled snapshot; implement the registry writer and unresolved external
references; add the fault tests (preserved mtime, add/delete, case change,
corrupt sidecar and views, interrupted publication, startup race) and the
scaling benchmark; and land the project-scoped publication lease.
