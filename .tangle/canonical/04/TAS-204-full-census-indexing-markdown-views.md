---
status: active
context_rev: 2
priority: P0
updated: 2026-09-15T19:44:02Z
summary: Implement full-census indexing and generated Markdown views.
next: Implement durable cross-project external references and their unresolved state.
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
surface; implement the registry writer and unresolved external
references; add the fault tests (preserved mtime, add/delete, case change,
corrupt sidecar and views, interrupted publication, startup race) and the
scaling benchmark; and land the project-scoped publication lease.

## Slice: pre-dispatch hash census and its diagnostic surface

Implemented the pre-dispatch canonical-store hash census. Every project-scoped
interaction that maintains derived state now enumerates the complete canonical
store and reconciles the derived index before its body runs: `src/tangle/main.py`
calls the new `src/tangle/census.reconcile()` before `_dispatch`, ahead of the
unchanged post-dispatch `_maintain_index`, so a mutating command still publishes
its own delta and views before returning. Discovery is the authority-bearing
`store.iter_node_paths` set, so `views/`, `proposals/`, `acceptances/`,
`receipts/`, and non-`.md` temporary files are excluded. The reconciliation is
`index.refresh`, which hashes every node's exact bytes, writes only the changed
node, edge, and full-text rows, deletes vanished rows, and rebuilds from
Markdown on sidecar loss; mtime, size, inode, watchers, and Git never substitute
for the digest. The four commands that own their own state (`init`, `index`,
`migrate`, `check`) are excluded from the pre-dispatch census, matching the
post-dispatch upkeep set, so `check` still writes no state and a fresh vault
with no sidecar creates none.

The new `tangle census` verb (`src/tangle/census.py`, dispatched from `main.py`
because `cli.py` and `sidecar.py` are frozen observables) is the dedicated
diagnostic surface. It reports `census` (reconciled/uninitialized/unavailable/
busy/failed), `root`, `changes` (canonical node files new or changed), `edges`,
`removed` (vanished node rows), and `views` (`current (N)`, `updated N`,
`failed: ...`, or `unavailable`); it republishes only the disposable views and
never writes canonical Markdown or creates local state. A routine read-only
interaction stays silent on a successful no-op.

Evidence: `tests/test_census.py` (7 cases) pins a direct edit observed before
the diagnostic answers, zero-change vs N-change reporting, the view
current->updated->current transition, a preserved-mtime same-size byte change
detected by hash alone, a removed node counted, a proposal/receipt/temporary
file excluded, and a fresh vault reported without creating a sidecar or view.
`make test` passed (848 passed, 3 skipped, 80 deselected); `uv run pytest -q
tests/test_memory_authority.py` passed (22 passed), proving the seven frozen
observable files are unchanged; `./scripts/tangle check` passed (251 nodes).

Remaining, in order: implement the registry writer and unresolved external
references; add the fault tests (preserved mtime, add/delete, case change,
corrupt sidecar and views, interrupted publication, startup race) plus the
scaling benchmark; and land the project-scoped publication lease. The corrupt-
sidecar fault tests must also cover the two review follow-ups on this module: a
duplicate `nodes_fts` row for one id is invisible to the dict-keyed content
comparison, and a non-numeric stored `next_value` raises through `int()` so
`tangle index` tracebacks instead of repairing; the scaling benchmark should
record the per-interaction cost of reading every full-text row.

## Slice: reconciled reindex for the sidecar query verbs

Made the derived-index repair entry point reconcile incrementally. The body of
`index.reindex` in `src/tangle/index.py` now defers to the existing
`index.refresh` and then returns the stored totals from `SELECT COUNT(*) FROM
nodes` and `SELECT COUNT(*) FROM edges`, keeping the `(nodes, edges, root)`
signature. `refresh` writes only the rows the Markdown changed, opens no write
transaction on an unchanged vault, and writes every row from the same snapshot
when the stored identity set is empty or differs from Markdown, so `tangle
index` reports unchanged `nodes: N` / `edges: M` totals and rebuilds a lost or
foreign index. Because the pre-dispatch `census.reconcile()` already reconciles
before dispatch, the in-verb `index.reindex` calls at `cli.py:400` (`_search`),
`cli.py:490` (`_backlinks`), and `cli.py:531` (`_stale`) now pay a snapshot read
instead of a whole-index rebuild, and `cli.py` stays byte-identical at HEAD.

Evidence: `tests/test_tangle_index.py` adds
`test_reindex_reconciles_incrementally_on_a_settled_vault`, which seeds the
fixture vault, runs the real `index` process twice, asserts both runs report
`nodes: 4` and `edges: 5`, and asserts the per-node `indexed_at` stamps read
back from the sqlite sidecar are identical across the two runs. It crosses a
one-second `indexed_at` boundary between the runs, so the old whole-index
rebuild would necessarily have restamped every row and failed the assertion
while the incremental reconciliation leaves the settled rows untouched. No
prompt-observable file changed.

## Slice: repair identity-preserving sidecar corruption

Closed the P1 gap the reconciled-reindex review left open. `index.refresh` in
`src/tangle/index.py` reconciled only the `(path, content_hash)` identity rows,
so a sidecar whose identity rows survived while its derived `nodes_fts` content
or its `id_sequences` reservations were lost exited 0 while leaving that state
unrepaired. `refresh` now reads the desired full-text content, the stored
full-text rows, and the stored reservations from the snapshot it already
parses, so the completeness check adds no asymptotic cost. Its early-return
guard additionally requires `nodes_fts` to match the Markdown exactly and every
prefix reservation to be at least the Markdown maximum plus one. The write
transaction rewrites each stale or absent full-text row for a node whose
identity row was unchanged, deletes an orphan full-text row, and raises the
reservations from the same `maxima` the guard compared. An unchanged vault
still opens no write transaction, so a settled vault pays the two extra reads
and no write, and the returned index converges from its identity rows to the
full derived projection: full-text content and reservations included. A
duplicate full-text row for one id and a non-numeric stored reservation remain
unrepaired and are recorded in the fault-test remaining item above.

Evidence: `tests/test_index_upkeep.py` adds
`test_identity_preserving_sidecar_corruption_is_repaired`, which builds the
index, captures the `search` answer for the seeded term, empties `nodes_fts`
and `id_sequences` through sqlite3 while asserting the node and edge rows are
unchanged, then runs `tangle index` and asserts it exits 0 with no stderr, that
the same `search` result matches again, that the `IDX` and `TAS` reservations
are back at 2, and that the identity rows are still unchanged. The
pre-change `refresh` fails it: a direct reproduction against the pinned sidecar
left `nodes_fts` and `id_sequences` empty and `search` reporting zero matches,
while the changed `refresh` restored both and left a second `index` run
writing nothing.

## Slice: project registry writer

Added the write side of the external-project registry so the durable
`.tangle/projects.json` the generated `projects.md` view already reads can be
created and updated without hand-editing. The new `src/tangle/project_registry.py`
serves `tangle project register ALIAS UID [--path PATH]`, dispatched from
`src/tangle/main.py` because `cli.py` and `sidecar.py` are frozen observable
files. It validates the alias through the new public
`identity.is_project_alias` (the module never duplicates the private regex) and
the UID through `identity.is_project_uid`, and it writes
`<vault.resolve(migrate_legacy=False)>/projects.json` through a same-directory
process-unique temporary file and `os.replace`, creating the vault directory
when absent. A missing file starts an empty registry; a malformed file (invalid
JSON, non-object, or a non-object `projects`) exits 1 and is never clobbered. A
new alias is added, an alias already bound to the same UID has its `path`
updated with every other key on the entry preserved, and an alias bound to a
different UID exits 1 with a clear message and no write. The reader's top-level
alias-map form is accepted on read; the writer always normalizes to
`{"projects": ...}`. Success prints `alias`, `project`, `path`, and the
absolute `registry` path and exits 0; a malformed command line exits 2 and a
malformed or conflicting registry exits 1. `help.py` gains the `project` group
and its `project register` entry under the coordination topic.

Evidence: the new `tests/test_project_registry.py` covers the normalized write
and the published `projects.md` alias and UID, invalid alias and UID usage
errors that write nothing, an empty registry created, a same-UID path update, a
same-alias different-UID conflict that leaves the file byte-identical, a
malformed registry that exits 1 byte-unchanged (invalid JSON, array, string, and
non-object `projects`), `--path .` rendered present and a missing path rendered
unavailable, unrelated aliases and unknown entry keys preserved, the top-level
alias map normalized, `--path=PATH`, and extra operands or a valueless `--path`
as usage errors. `tests/test_skill.py` adds `project` and `project register` to
`_PUBLIC_VERBS`, so both verbs keep bounded help. No frozen file changed.

# Frozen blocker

The sidecar query verbs no longer need a `cli.py` edit: the non-frozen
`src/tangle/index.py` route landed, so `index.reindex` — which `cli.py:400`
(`_search`), `cli.py:490` (`_backlinks`), `cli.py:531` (`_stale`), and
`_run_reindex` at `cli.py:224` all call — reconciles incrementally through
`index.refresh` instead of rebuilding the whole index per call, and the
pre-dispatch census already reconciles before dispatch. `cli.py` stays
byte-identical at HEAD.

The only remaining frozen dependency is the project-scoped publication lease,
which needs `src/tangle/sidecar.py`. That file is one of the prompt-observable
files pinned by `benchmark/memory-authority-result.json`, so a byte change there
owes a faithful LIVE authority re-record —
[[TAS-188-remove-uv-from-quality-benchmark-reproduction]] is the blocked owner
of that gate — which this session is not authorized to run. That slice
therefore remains blocked on an authorized re-record or a non-frozen route, the
established pattern that reaches a verb's answer through a new module as
`tangle.allocate` and `tangle.census` do. This slice deliberately did not edit
any frozen file.
