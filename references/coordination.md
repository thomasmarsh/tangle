# Coordination reference

Load this before any coordinated or multi-writer work: claims, leases, parallel
worktrees, integration, and reconciliation. It is the canonical Markdown source
that `braintree help coordination` prints, and it is installed beside
`SKILL.md` at the same revision as the `braintree` command.

## Hybrid sidecar contract

Use the installed `braintree` command for graph indexes and live coordination.
Do not have workers read or write SQLite directly. The sidecar is an untracked
external database keyed by the Git common directory and shared by all worktrees;
`BT_SIDECAR_DIR`/`BT_PROJECT_ID` override it for tests.

- Markdown stays authoritative; SQLite is authoritative only for local
  operational coordination.
- `braintree index [.braintree]` rebuilds derived node, edge, content-hash, backlink,
  stale-pin, and full-text data from Markdown; `braintree search`,
  `braintree backlinks`, and `braintree stale` reconcile first.
- Run `braintree init` before coordinated work. Loss of the database may lose
  claims and indexes but never durable graph knowledge; recover with
  `braintree init` then `braintree index`.
- The sidecar is for concurrent processes on one host and a local filesystem; it
  refuses a network-mounted location unless overridden. For multi-host
  coordination use a server database such as PostgreSQL; SQLite/WAL is not that
  service.
- Keep status directories and Markdown pointers. A stationary-path/status-in-
  database migration is deferred.

## Hash, claim, and lease

- NODE is a bare ID (`TAS-085`) or a full node name, the filename stem
  (`TAS-085-hash-addressing-and-operand`); a path
  (`.braintree/proposed/TAS-085-hash-addressing-and-operand.md`) is not accepted, and
  the error names the two accepted forms. `braintree hash` resolves either form,
  but `claim` and `release` never read Markdown: they treat NODE as the opaque
  claim key, so address one node with the same spelling in every command.
- `braintree hash NODE` prints `node` and `content_hash`: the SHA-256 hex digest
  of the node file's raw UTF-8 bytes, frontmatter included. The `content_hash`
  value is the operand: take that bare 64-character digest from `braintree hash`
  rather than reimplementing the algorithm, and pass it as `--base-hash` to
  `braintree claim` and `braintree release`; never pass the `node:`/
  `content_hash:` block or any other spelling.
- `braintree claim NODE AGENT --base-hash HASH [--lease-seconds N]` acquires or
  renews an exclusive lease, and `braintree release NODE AGENT --base-hash HASH`
  releases it. The release hash must be the starting hash recorded by the claim:
  a hash or owner mismatch fails non-zero and names the cause.
- A lease lasts 900 seconds by default, `--lease-seconds N` chooses another
  duration, and a claim that repeats the same agent and base hash renews the
  lease to a fresh `N` seconds rather than failing or keeping the old expiry.
  `claim` and `release` report `lease_remaining_seconds` on every call, and
  `release` distinguishes a lapsed matching lease (`expired`) from a node that
  holds no claim at all (`no-op`).
- A worker hashes and claims before editing, and the node's own frontier
  transition — the status move and the `# Context` edit that take the frontier —
  is part of the claimed edit, not a precondition: the recorded `content_hash`
  names the node content exactly as handed off, before that transition and
  before any other edit.

```sh
hash=$(braintree hash TAS-085-hash-addressing-and-operand | sed -n 's/^content_hash: "\(.*\)"$/\1/p')
braintree claim TAS-085-hash-addressing-and-operand worker --base-hash "$hash"
braintree release TAS-085-hash-addressing-and-operand worker --base-hash "$hash"
```

## Parallel worktree contract

`# Focus`, `priority`, and `active` status are advisory navigation, never a work
claim. A coordinator assigns each worker a direct node path and an exclusive
write set before work begins.

- One agent writes a node and its status path at a time. Shared parents,
  `index-map.md`, definitions, and root hubs are coordinator-owned unless their
  writes are explicitly serialized.
- A worker may author the minimal primitive or seam a gate or `Done when`
  criterion needs inside its declared write set, and records that authored piece
  in the node's `# Result`. A change that alters a landed seam another node owns,
  or the public schema contract, is escalated rather than authored. A
  coordinating task names any primitive or seam its slice must introduce, so the
  worker does not have to infer it.
- Additive, optional fields are the exception: an additive, optional,
  behavior-preserving field on a seam a resolved sibling owns, when the assigned
  node's `Done when` requires it, is authored by the assigned worker rather than
  escalated. The worker records the field and the affected consumer in its own
  `# Result` and does not edit the resolved node; mechanical literal updates in
  the owner's tests stay inside the consumer's write set; and the coordinator
  decides at integration whether the owner's `context_rev` needs a bump.

- An internal, non-behavioral reuse change in a resolved node's module —
  widening an item to `pub(crate)`, or adding a `pub(crate)` helper an existing
  private item delegates to — is authored by the assigned worker without
  escalation when it changes no artifact byte, no public API, and no behavior.
  The worker records the widened items, the reason (one spelling instead of
  two), and the resolved owner in its own `# Result`; it does not edit the
  resolved node and does not bump its `context_rev`, because no consumer
  assumption changes. Visibility and `pub(crate)` factoring are not seam
  alterations unless a consumer outside the crate or an artifact shape changes,
  and duplicating the seam inside the new module is preferred over escalating
  when reuse would otherwise copy the spelling.

- The assigned write set is the compile-and-golden closure of the approved
  change, not a crate directory: membership covers every file the change must
  touch, including exhaustive matches and struct literals on the changed types,
  plus every golden and baseline the change can invalidate (`tests/golden/**`,
  `baselines/**`), the workspace manifest and lockfile when the approved change
  needs a dependency, and the generated artifacts a source shape change
  invalidates (JSON schemas, snapshots, pinned-hash fixtures). A necessary
  dependency or regenerated artifact is in the set even though the change edits
  no source file in it, so a worker never leaves its set or stops for a closure
  file. When the closure exceeds the assigned set, the worker includes and
  reports the additional in-scope paths; it stops and escalates for a path owned
  by another node or a shared hub.
- A worktree is a snapshot, not global truth; workers do not assume unseen work
  or IDs are unclaimed.
- A worktree slice is not a node boundary: a fresh worker may continue the
  assigned node, and the worker keeps the assigned node's content update and its
  status move coherent in one commit or handoff bundle.
- The coordinator integrates child evidence, reconciles upstream change, and
  alone resolves a coordinating parent after all required child work is
  integrated.
- Independent slice verification rests on falsifiable evidence: a verifying actor
  that can execute the gates, or a coordinator-run gate transcript attached to
  the handoff. A read-only, no-execution reviewer sign-off alone does not falsify
  a recorded gate claim, so it can never be the sole sign-off; when only such a
  reviewer is available, the coordinator reruns the gates and attaches the
  transcript it verifies.
- For parallel creation, use `braintree allocate PREFIX` to atomically reserve an
  ID; Coordinator preallocation or explicitly disjoint numeric ranges are valid
  offline alternatives. A local `find` checks for an existing collision only; it
  is never an ID reservation. Branch-local `owner` or claim metadata is
  insufficient because separate worktrees can make the same claim without seeing
  each other. An allocated id is burned permanently: the counter only advances,
  so an allocation the caller discards is never returned and never reused, and
  `braintree reservations` lists each prefix's burned ids — reserved with no
  node on disk — so a gap in the vault is a discarded allocation, not a missing
  node. There is no release or reclaim: a reused id could collide with a node an
  in-flight worktree already wrote under it, and the sidecar cannot distinguish
  a discarded allocation from a pending one.

## Worker handoff

Before editing, a worker records the integration base and its assigned node path
and write set, hashes its starting Markdown node with `braintree hash`, and claims
it with `braintree claim`. `braintree hash` takes the node's bare ID or full node
name, never the path the handoff supplies, and its `content_hash` field is the
bare digest passed as `--base-hash`; `claim` and `release` treat NODE as the same
opaque claim key. The base hash names the node content as handed off: the node's
own frontier transition — the status move and `# Context` edit — belongs to the
claimed edit, not to the handoff. Before handoff, verify every changed, created,
and moved path remains in that assigned write set, then release the matching
claim. Report the base, touched paths, created paths, moved paths, dependency
evidence, and test evidence to the coordinator.

A handoff that orders reuse of an existing artifact names its concrete path — or
the node that owns it — so the worker reads an input instead of inferring a
shape. A worker that cannot resolve an ordered artifact to a path or an owning
node does not invent it: it stops and asks the coordinator, because a fabricated
artifact silently becomes the interface a downstream slice consumes. When the
ordered artifact is new, the handoff or the node's plan declares its path and
format before the worker authors it, so a downstream consumer is handed a named
artifact rather than an inferred one.

A handoff whose write set excludes the coordinating parent cannot advance its
`next`. Either the handoff names the parent — or the parent's `next` line — in
the write set, so the resolving worker owns the advance, or the coordinator owns
the advance and the worker reports the stale route as its handoff action instead
of editing outside its set. A stale route is an unfinished coordinating node
whose `next` is a single direct-child link naming an already-resolved child;
`braintree check` reports it as `next-resolved-node`.

Resolving the parent's `next` child is the frontier transition that completes
the slice, and what the worker commits and hands off follows from the write set:

- The write set names the parent — or the parent's `next` line: the worker
  advances the parent's `next` to the next deliberate child, or removes `next`
  when the resolved child was the last one, refreshes the parent's `updated`,
  leaves its `context_rev` unchanged, and commits that advance in the same
  commit as the child's resolution. No commit then leaves the parent routing to
  a resolved child, and the coordinator pays no round trip for the advance.
- The write set excludes the parent: the child's resolution commit is the
  worker's completion, and the pending advance is the handoff. The worker names
  the parent and the resolved child, records the pending advance as its handoff
  action instead of editing outside its set, and verifies its slice with
  `braintree check --allow-pending-advance PARENT`, whose operand is the
  parent's node name or bare id.

The window between the child's resolution and the parent's advance is the
multi-writer transient: the parent's `next` names an already-resolved child
while its advance is still owed, so an unfinished handoff produces it by design,
and the failure appears the moment the child's file moves, before any commit. A
genuine stale route is the same Markdown with no pending advance behind it, and
no file content separates the two: the checker is stateless and reads the same
graph either way. `braintree check` therefore separates them by declaration
rather than by inference. `--allow-pending-advance NODE` sanctions exactly the
one named parent whose `next` names an already-resolved child and relaxes
nothing else — the resolved node's status move, the direct-child route, the
pins, the orphan route, and every other finding still fail — while the
unsanctioned state stays the `next-resolved-node` failure. The sanction never
clears the advance: the coordinator's integration gate is the plain
`braintree check`, so a route that is stale rather than pending still fails
integration, and the coordinator owns the advance, the plain gate, and the
parent's `updated`.

A worker records a compact structured completion receipt before its long
narrative report: the recorded base hash, the `release` result, a gate summary,
and the commit SHAs. A `release` result at the recorded base hash is the
completion signal the coordinator trusts over the run status: when a run times
out while the worker is still composing prose, that release states the work is
finished even though the run reported failure.

Serial work uses the same discipline without branches: self-assign one node and
write set, claim it, keep content and status coherent, run
`braintree check`, and do not leave a resolved status move uncommitted.

## Timed-out worker recovery

A timed-out run leaves a partial state, not a lost one, and recovery is a
coordinator decision taken on evidence rather than a rerun. Do not revert or
discard the partial diff unread: inspect it and run the tests the diff touches to
establish whether that partial state is behavior-preserving.

- When the partial state compiles and its touched tests pass, it is green: either
  re-dispatch a narrow finishing brief for the remaining slice — the tests, the
  `# Result` evidence, and the status move the timed-out worker never reached —
  or accept the coherent slice on the same node instead of reverting it, because
  reverting a compiling, passing slice discards work for no gain. The node stays
  `proposed` until the finishing worker resolves it.
- When the partial state does not compile or fails a touched test, it is not
  green: revert it and re-scope the remaining slice against the reverted base
  rather than continuing on a state whose behavior is unknown.
- A run that timed out after resolving its node and splitting the remainder needs
  only coordinator verification: the resolved node, its recorded evidence, and
  its advanced `next` route are the finished slice, so verify them instead of
  re-deriving the work.

## Integration and reconciliation

The coordinator integrates worker branches one at a time. Never blindly
auto-merge an upstream change to the assigned node or divergent status paths:
reject that handoff or perform manual semantic reconciliation before integration.
After each integration, run `braintree check`, use the line-anchored
`rg -n '^Depends on \[\[[^]]+\]\] at context_rev [0-9]+\.' .braintree` search for
every context-bearing dependency changed by that handoff, and reconcile stale
consumers before their dependent execution. The `^` anchor matches an authored pin
line rather than the command text where a node quotes it, so a zero-consumer
reading needs no inspection. Resolve a coordinating parent only after its required
child evidence has been integrated.

Resolution authority is the coordinator's. After required children are
integrated, the coordinator alone performs a coordinating parent's resolving
edit: moving it to `resolved`, writing the outcome's evidence and limitations,
and removing `next`. A worker slice prepares closeout evidence only — its result,
limitations, and test and dependency evidence — and never moves the coordinating
parent to `resolved`; a delegated closeout task stops at the handoff, leaving the
resolving edit to the coordinator.
