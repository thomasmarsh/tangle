# Coordination reference

Load this before claims, leases, parallel or multi-writer work, worktree
handoffs, integration, or reconciliation. It is the canonical Markdown printed
by `tangle help coordination` and is installed with `SKILL.md` and the
command.

## Local coordination

Use `tangle` for derived answers and live coordination. A client never reads
or writes the local coordination state directly and never maintains a derived
index by hand. The untracked, per-project store is shared by all worktrees of
one repository.

- Markdown remains authoritative. The local state holds only derived answers
  (search, backlinks, stale pins) and live coordination (claims, leases,
  reserved IDs); losing it loses no durable graph knowledge.
- The derived index maintains itself on every interaction.
  `tangle index [.tangle]` exists only to repair or rebuild it from
  Markdown after loss or damage.
- Local state coordinates concurrent processes on one host and local
  filesystem. Across hosts, coordinate through the shared Markdown vault.
- The node's authoritative `status` field and Markdown pointers remain
  authoritative, not local-state fields.

## Hash, claim, and lease

NODE is a bare ID (`TAS-085`) or full filename stem
(`TAS-085-hash-addressing-and-operand`), never a path. `tangle hash` resolves
either spelling; `claim` and `release` do not read Markdown and they treat NODE
as the opaque claim key, so use the same spelling throughout one handoff.

`tangle hash NODE` prints the SHA-256 `content_hash` of the raw node bytes.
Pass that bare 64-character value as `--base-hash` to `claim` and `release`;
do not reimplement the hash or pass the output block. A worker hashes and claims
before editing. The starting hash covers the handed-off node before its frontier
status change or `# Context` edit, which belong to the claimed work.

`tangle claim NODE AGENT --base-hash HASH [--lease-seconds N]` acquires or
renews an exclusive lease. A lease lasts 900 seconds by default; repeating the
same agent and base hash renews it for a fresh duration. `tangle release NODE
AGENT --base-hash HASH` requires the claim's starting hash and owner. Both
commands report `lease_remaining_seconds`; `release` distinguishes a lapsed
matching lease (`expired`) from no claim (`no-op`).

```sh
hash=$(tangle hash TAS-085 | sed -n 's/^content_hash: "\(.*\)"$/\1/p')
tangle claim TAS-085 worker --base-hash "$hash"
tangle release TAS-085 worker --base-hash "$hash"
```

## Parallel worktree contract

`# Focus`, priority, and `active` status are navigation, not claims. A
coordinator assigns each worker a direct node path and an exclusive write set
before work begins. Before dispatch, the brief names the known resolved-sibling
compiler seams the approved change can force — the concrete paths or the
resolved owners — so a mechanically required conformance edit is not first
discovered as an owned-seam escalation. A seam citation in a large module
prefers `path (Symbol)` — the owning call-site function — over a bare
`file:line`, because the same helper can be invoked from a different compilation
stage than the field it must read.

- One agent writes a node and its status field at a time. Shared parents,
  `index-map.md`, definitions, and root hubs are coordinator-owned unless their
  writes are explicitly serialized.
- A worker may author the minimal primitive or seam required by its gate or
  `# Done when` inside its write set and records it in `# Result`. Escalate a
  change to another node's landed seam or the public schema contract. A
  coordinating task names any primitive or seam its slice must introduce.
- An additive, optional, behavior-preserving field on a seam a resolved sibling
  owns, when the assigned node's `Done when` requires it, is authored by the
  assigned worker rather than escalated. The worker records the field and the
  affected consumer in its own `# Result` and does not edit the resolved node;
  mechanical literal updates in the owner's tests stay inside the consumer's
  write set. The coordinator decides at integration whether the owner's
  `context_rev` needs a bump.
- An internal, non-behavioral reuse change in a resolved node's module —
  widening an item to `pub(crate)`, or adding a `pub(crate)` helper an existing
  private item delegates to — is authored by the assigned worker without
  escalation when it changes no artifact byte, no public API, and no behavior.
  The worker records the widened items, the reason (one spelling instead of
  two), and the resolved owner in its own `# Result`; it does not edit the
  resolved node and does not bump its `context_rev`, because no consumer
  assumption changes. Visibility and `pub(crate)` factoring are not seam
  alterations unless a consumer outside the crate or an artifact shape changes;
  duplicating the seam inside the new module is preferred over escalating when
  reuse would otherwise copy the spelling.
- The assigned write set is the compile-and-golden closure of the approved
  change, not a crate directory. It includes exhaustive matches and struct
  literals on the changed types; every golden and baseline the change can
  invalidate (`tests/golden/**`, `baselines/**`); the workspace manifest and
  lockfile when the approved change needs a dependency; and the generated
  artifacts a source shape change invalidates (JSON schemas, snapshots,
  pinned-hash fixtures). A worker includes and reports the additional in-scope
  paths discovered in that closure. A compiler- or touched-test-forced
  conformance edit — an exhaustive match, constructor, fixture, or derived
  consumer — is in the change's closure even when a resolved sibling owns the
  path, whether named before dispatch or discovered only by the compiler or a
  touched test; the worker makes the mechanical edit and reports it with the
  closure rather than escalating. The worker still stops and escalates when the
  change alters the seam's behavior, its public contract, or the meaning of the
  landed seam, or when the path is owned by another node or a shared hub and
  neither the compiler nor a touched test mechanically forces it.
- A worktree is a snapshot, not global truth; unseen work and IDs may be
  claimed. A worktree slice is not a node boundary, and a fresh worker may
  continue the same node. Keep its content update and status change coherent.
- The coordinator integrates child evidence and alone resolves a coordinating
  parent after all required work is integrated.
- Verification needs falsifiable evidence from an actor that ran the gates or a
  coordinator-run gate transcript. A read-only reviewer cannot be the sole
  sign-off.
- New canonical ids come from cryptographic entropy at admission, so parallel
  creation needs no reservation, shared sequence, or preallocated range. For a
  legacy numeric prefix during the compatibility window only, reserve an ID, or a
  batch of `COUNT` consecutive ids in one call in a single transaction, with
  `tangle allocate PREFIX [COUNT]`, or use coordinator-preallocated,
  explicitly disjoint ranges offline. `find` only detects collisions. An
  allocated id is burned permanently: an allocation the caller discards is
  never returned and never reused. `tangle reservations` lists each prefix's
  burned ids — reserved with no node on disk — so a gap in the vault is a
  discarded allocation, not a missing node. There is no release or reclaim
  because an in-flight worktree may already contain the ID.

## Worker handoff

Before editing, record the integration base, direct node path, and write set;
hash and claim the starting node. Before handoff, confirm every changed,
created, and moved path is in the write set, release with the starting hash, and
report the base, paths, dependency evidence, and gate evidence.

A handoff that orders reuse of an existing artifact names its concrete path —
or the node that owns it — so the worker reads rather than infers the input. A
worker that cannot resolve an ordered artifact to a path or an owning node does
not invent it: it stops and asks the coordinator. When the ordered artifact is
new, the handoff or the node's plan declares its path and format before it is
authored.

When a frontier child resolves, its coordinating parent's `next` must advance:

- If the write set names the parent or its `next` line, the worker advances or
  removes `next`, refreshes the parent's `updated` without bumping
  `context_rev`, and includes the advance in the child's resolution commit.
- Otherwise the worker cannot edit the parent. A handoff whose write set
  excludes the parent cannot make that edit: the child's resolution commit
  completes the worker's slice and the pending advance is its handoff action.
  Name the parent and resolved child, then verify with
  `tangle check --allow-pending-advance PARENT`. When the node being resolved
  is the current `next` of a parent outside the write set, its acceptance line
  names that exact command rather than the plain gate, and the report surfaces
  the pending advance as the coordinator's integration action.

A stale route is an unfinished coordinating node whose `next` is a single
direct-child link naming an already-resolved child; `tangle check` reports it
as `next-resolved-node`. The window between the child's resolution and the
parent's advance is the multi-writer transient: the parent's `next` names an
already-resolved child while its advance is still owed, and the failure appears
the moment the child's file moves, before any commit. A genuine stale route is
the same Markdown with no pending advance behind it; no file content separates
the two: the checker is stateless and therefore separates them by declaration
rather than by inference.

`--allow-pending-advance NODE` sanctions exactly the one named parent whose
`next` names an already-resolved child and relaxes nothing else. The sanction
never clears the advance: the coordinator's integration gate is the plain
`tangle check`, and the coordinator owns the advance and parent timestamp.

A worker records a compact structured completion receipt before its long
narrative report: the recorded base hash, the `release` result, a gate summary,
and the commit SHAs. A `release` result at the recorded base hash is the
completion signal the coordinator trusts over the run status when a run times
out while the worker is still composing prose.

Serial work follows the same discipline without branches: self-assign the node
and write set, claim it, keep its content and status coherent, run
`tangle check`, and commit its resolved move.

## Timed-out worker recovery

A timed-out run leaves a partial state, not a lost one: inspect it and run the
tests the diff touches to establish whether that partial state is
behavior-preserving.

- If it compiles and touched tests pass, re-dispatch a narrow finishing brief
  for the remaining slice or accept the coherent slice on the same node instead
  of reverting it. The node stays `proposed` until the finishing worker resolves
  it.
- If the partial state is red on one localized, understood case while the rest
  is green, a narrow repair is authorized only when the failure is reproducible,
  localized to the intended change, its cause and repair write set are
  understood, and the remaining touched gates are green: retain the partial slice
  and record that evidence, the bounded repair brief, and the branch taken. When
  any of those conditions is not established, revert it and re-scope the
  remaining slice against the reverted base rather than continuing on a state
  whose behavior is unknown.
- If it does not compile, or a touched test fails outside the localized-red
  conditions above, revert it and re-scope the remaining slice against the
  reverted base.
- If the run timed out after resolving its node and splitting the remainder, it
  needs only coordinator verification of the node, evidence, and advanced
  route.

## Integration and reconciliation

Integrate worker branches one at a time. Never blindly auto-merge an upstream
change to the assigned node or divergent status paths; reject the handoff or
reconcile it semantically. After each integration, run `tangle check` and use
the line-anchored
`rg -n '^Depends on \[\[[^]]+\]\] at context_rev [0-9]+\.' .tangle` search
for each dependency changed by the handoff. The anchor matches authored pins,
not the command text where the recipe is quoted, so zero results need no further
inspection. On integration, compare each submitted `updated` with the
integration base: replace a fresh future stamp introduced by the submitted
mutation with a fresh host-clock reading, but preserve and report a future stamp
the base already carried as an inherited clamp rather than moving it backward.
Reconcile stale consumers before they execute.

Resolution authority is the coordinator's. After all required child evidence
is integrated, the coordinator alone performs a coordinating parent's resolving
edit: move it to `resolved`, record evidence and limitations, and remove `next`.
A worker prepares closeout evidence but never resolves the coordinating parent;
a delegated closeout stops at handoff.
