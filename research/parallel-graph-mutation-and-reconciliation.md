# Parallel graph mutation and reconciliation

Status: exploratory research. This document describes a possible foundation; it
does not change the Tangle contract.

Any implementation of this foundation should be pay-for-what-you-use. Ordinary
single-writer work remains direct Markdown editing under the existing Tangle
contract. The proposal, reconciliation, and receipt machinery is an opt-in
coordination path for asynchronous, overlapping, or independently hosted work,
not a new checklist imposed on every graph mutation. An implementation may use
the same normalized ingestion model internally for all changes, provided the
ordinary path does not require an agent to author or reason about that machinery.

## Problem

Tangle deliberately makes each node a directly editable Markdown file. That
removes the global-index merge hotspot, but it does not make arbitrary concurrent
graph edits safe. Two agents can still:

- create different nodes for the same durable outcome;
- edit or move the same node from different snapshots;
- update a dependency and execute a consumer against the old revision;
- resolve siblings while racing to advance a shared parent's `next`;
- discover that their assigned outcomes should be split, consolidated, or
  superseded;
- produce individually valid branches whose union violates a graph invariant.

The current coordination contract handles these situations by giving a
coordinator exclusive write sets and a serial integration role. That is a good
operating discipline, but it assumes an orchestration shape that Tangle cannot
require. A pair-programming agent, a background worker pool, several worktrees,
and several hosts may all need the same lower-level mechanisms.

The design question is therefore not "how can every agent edit the graph at
once?" It is:

> How can many actors contribute asynchronously without making their partial
> views authoritative, while any later integrator can deterministically discover,
> compare, disposition, and apply those contributions?

## What exists today

The repository already contains several useful pieces of this foundation.

### Low-contention canonical storage

Nodes live in separate files and status is encoded by directory. Unrelated node
edits usually have disjoint Git paths. `index-map.md` is routing-only, and the
SQLite index is derived rather than committed, so routine mutations do not also
rewrite a shared ledger. The benchmark's worktree screen demonstrates clean
integration of disjoint assigned node edits.

This reduces textual conflicts. It does not resolve semantic overlap.

The status-directory benchmark that selected this representation measured path
changes, body reads, merge conflicts, and stale derived views before the current
multi-writer intake problem existed. A stable canonical path now has additional
potential value: receipts and external tools retain one locator, a status
transition is no longer confused with deletion, and globally unique identities
can be created without coordinating a numeric sequence. Those are new criteria,
not evidence that the earlier benchmark was wrong, so stationary storage should
be reevaluated under the derived-index architecture rather than assumed or
rejected from the earlier result alone.

### Same-host identity and exclusion

The external SQLite sidecar is keyed by Git's common directory, so all local
worktrees share atomic ID sequences and node claims. `tangle allocate` burns
IDs rather than risking reuse, and `tangle node record` reserves before using
exclusive file creation. Claims record an opaque agent ID, a caller-supplied base
content hash, and a lease expiry.

These are valuable primitives, with narrower guarantees than a general
multi-writer protocol:

- a claim excludes another conforming local claimant for one opaque node key;
- it does not claim a multi-node write set or a graph invariant;
- `claim` does not itself verify that the supplied hash is the current Markdown
  hash;
- claims and allocations are intentionally disposable and same-host only;
- claim ownership is not durable provenance and active claims are not exposed as
  a detailed work queue;
- the vault-local reservation fallback is atomic only inside the filesystem that
  contains it, not across independent worktree copies or hosts.

### Structural validation

`tangle check` validates the canonical graph after edits. It detects duplicate
identities, invalid routes, stale pins, and lifecycle errors. The
`--allow-pending-advance` exception precisely represents one known multi-writer
transient without weakening unrelated checks.

This is an important pattern: name a bounded transient, make it explicit, and
keep the ordinary acceptance gate strict.

### Read-only reconciliation planning

`tangle reconcile --base ... --head ...` reads Git snapshots and reports:

- duplicate identities;
- the same node changed by more than one head;
- dependency revision changes followed by affected base consumers.

It is conservative and useful, but it is a hazard report, not a merge engine. It
does not apply changes, represent uncommitted contributions, identify semantic
duplicates with different IDs, reason about deletions or restructuring as
first-class operations, or record how a hazard was resolved. Its dependency view
is calculated from the submitted snapshots rather than from a validated
hypothetical merged graph.

## Observations

### Git conflicts are only one class of conflict

There are at least four layers:

1. **Transport conflict:** two branches cannot be combined textually.
2. **Identity conflict:** two paths claim the same Tangle ID.
3. **Invariant conflict:** the combined files violate routing, lifecycle,
   dependency, or frontier rules.
4. **Meaning conflict:** two valid nodes own the same outcome, two edits express
   incompatible conclusions, or execution reveals a different node boundary.

Git handles the first incompletely. `tangle check` and today's reconciler
cover parts of the second and third. The fourth cannot be decided by a generic
text merge or a similarity score.

### Canonical-node concurrency is the wrong primary abstraction

Trying to make every field in a node concurrently writable would turn Markdown
into a distributed database protocol. Even a perfect text CRDT would not decide
whether two conclusions are redundant, whether `context_rev` should bump, which
child owns a newly discovered outcome, or which status is true.

The safer split is:

- make **contribution intake** commutative and append-only;
- make **canonical-state reduction** serialized, preconditioned, and validated.

This resembles a source-control review queue more than shared document editing.
The queue contains claims about desired graph changes, not another authoritative
copy of graph state.

### A coordinator is a role, not a required long-lived agent

Someone or something must serialize the instant at which a proposed state
becomes authoritative. It need not be a permanent coordinator agent. A CLI can
acquire an integration lease, construct a candidate graph in a temporary index
or worktree, require explicit dispositions for ambiguous cases, run the checker,
and compare-and-swap the expected Git head.

A rich orchestrator could assign semantic decisions to a coordinator. A simple
workflow could let the current agent perform the same role. A human could review
the plan. The invariants should be identical in all three cases. Acquiring an
integration lease establishes exclusion among conforming clients only. Tangle
does not determine who may update the canonical ref or who is entitled to settle a
semantic conflict; filesystem permissions, Git controls, an orchestrator, or human
process may impose those rules externally. The protocol merely requires an
ambiguous decision to be explicit rather than silently inferred.

### Actor identity is optional metadata, not authority

Agents and nodes are intentionally not one-to-one. Putting `agent:` into
canonical node frontmatter would invite stale ownership, confuse authorship with
authority, and create another mutable field. A proposal, decision, or receipt may
instead carry an optional opaque actor field appropriate to that event:
`producer_id`, `decision_actor_id`, or `integrator_id`. A proposal may also carry
an optional `run_id`.

Tangle preserves and exposes these caller-supplied values and includes them in
the sealed object's digest. It does not require them, authenticate them, require
uniqueness or stability, infer a role or permission from them, or use them to
accept or reject an operation. They are asserted provenance metadata for users and
external systems to interpret. Proposal and integration identities remain unique
even when every actor field is absent, duplicated, or misleading.

### Permanent node IDs should be assigned late

Cross-host proposals cannot safely share a local sequence. More importantly,
allocating canonical IDs while ideas are still redundant or subject to
consolidation creates needless burns and encourages proposal identity to become
graph identity.

A new-node contribution can use a proposal-scoped symbol, addressed globally as
`proposal_id#symbol`. The integrator generates the permanent
`tas`/`tho`/`def`/`dec`/`fbk` ID only when it admits the node, then records the
mapping in the acceptance record and receipt. References among nodes created by
one bundle use proposal-scoped symbols until that mapping is fixed.

Late assignment does not require a shared numeric sequence. The canonical payload
is exactly 128 bits encoded as 26 lowercase Crockford Base32 characters. Its
grammar is `[0-7][0-9a-hjkmnp-tv-z]{25}`: the restricted first character prevents
noncanonical 130-bit encodings, and the alphabet omits `i`, `l`, `o`, and `u`.
The payload is generated from acceptance-local cryptographic entropy or from a
domain-separated 128-bit digest of the proposal identity and local symbol, as the
versioned identity contract specifies. The type prefix remains part of the
identity (`tas-...`, `tho-...`, `def-...`, `dec-...`, `idx-...`, or `fbk-...`),
so a canonical node ID looks like
`tas-01k5v6m3x8f2q7c9d4hn8w2pza`. The content hash remains the version and
optimistic-concurrency witness. A hash of the current Markdown bytes must not be
the logical ID because an ordinary edit would change it; a hash of the initial
bytes would cease to be a content address.

Canonical identity spelling should be lowercase ASCII. A CLI may accept legacy or
mixed-case input and normalize it at the boundary, but newly stored filenames,
references, project aliases, and URI components use one lowercase spelling, and
duplicate detection compares normalized identities so case-sensitive and
case-insensitive filesystems cannot disagree. Existing uppercase numeric IDs
remain readable; any path migration uses an intermediate name rather than relying
on a case-only rename.

Compact human terminal views may render a collision-aware abbreviation such as
`tas-01k5v6m3...`: use at least eight payload characters and lengthen the prefix
deterministically until it is unique within the rendered result set. The ellipsis
marks it as presentation, not an identifier. Canonical Markdown, filenames,
wikilinks, proposals, plans, decisions, receipts, logs intended as durable
evidence, and structured or machine-readable output always carry the full ID. A
full-width terminal mode remains available, and no client is responsible for
choosing or maintaining abbreviations.

### Project identity and reference scope are distinct from node identity

A globally unique node ID makes an unqualified reference safe inside its own
project, but a reference to another project still needs durable authority and a
way to locate that project. Introduce a cryptographically random, immutable
128-bit project UID, encoded with the same 26-character lowercase Crockford
Base32 payload and a `prj-` prefix, committed with the vault and shared by its
clones. For example: `prj-04r8b1t7n2c6m9x3q5f0hkwdza`. This is distinct from
the current same-host sidecar identity derived from a Git common-directory path,
which is a local storage key and changes across clones.

A lowercase project alias such as `hekate` is presentation and local registry
state, not durable identity. Clients may accept a convenient spelling such as
`hekate:tas-01k5v6m3x8f2q7c9d4hn8w2pza`, with the unqualified node ID meaning
the current project, but a sealed proposal, receipt, or canonical cross-project
edge expands the alias to an immutable project UID. Aliases may be renamed or
collide; the UID settles identity and the registry settles local location.

Ordinary wikilinks remain local-vault references. A colon-qualified external
reference must not masquerade as an Obsidian wikilink: Tangle owns a separate
qualified reference or URI grammar and can project a registered external target
into a local Markdown link or proxy note. If the target project is not registered,
the durable external reference remains visible and unresolved rather than becoming
a broken local node or disappearing.

### Stable storage needs project-owned projections

A stationary canonical store should not make each client scan files, construct
status lists, copy summaries into aliases, or maintain symlinks. Tangle owns
those projections as an explicit side effect of its commands. One candidate
layout is a stable, optionally sharded path derived from the immutable ID, with an
immutable creation label for filesystem readability and authoritative `status`
inside the node. The exact path is a versioned format decision, not user-authored
indexing policy.

Generated Markdown view pages provide portable navigation without becoming a
second graph authority. They may group nodes by status, area, priority, recent
activity, or registered external project and render the current canonical summary
as link display text. They are deterministic, disposable, excluded from canonical
node discovery, and regenerated by Tangle; clients neither edit them nor copy
their contents into canonical nodes. Symlink status trees may be an optional view
backend, but correctness, discovery, and acceptance never depend on a link being
present or portable.

The derived index and views must account for direct Markdown edits made between
commands. Every project-scoped command that reads or mutates graph state begins
with a complete census of the canonical node store; global `--help`, `--version`,
installation, and equivalent repository-independent operations do not require a
vault:

1. enumerate every canonical node path, excluding proposals, receipts,
   acceptances, views, and temporary files;
2. read and hash every node's exact bytes rather than trusting modification time,
   size, an OS watcher, or a caller-supplied changed-path list;
3. compare the path, normalized identity, and digest set with the sidecar, parsing
   new or changed bytes, deleting vanished rows, and rebuilding affected edges,
   search entries, reservations, and other derived answers in one transaction;
4. answer the requested command only from that reconciled snapshot; and
5. when the command mutates canonical nodes, apply its known post-mutation index
   delta and atomically regenerate affected Markdown views before returning.

This is an `O(total canonical Markdown bytes)` verification pass per interaction,
with parsing and view writes proportional to detected changes. It is intentionally
stronger than an mtime shortcut: a point edit must be visible to the next command
even when timestamps are coarse, preserved, or misleading. A watcher or file
metadata may accelerate hints but cannot replace the hash census. Hash state is
derived and disposable; loss causes a full parse and view rebuild, never loss of
knowledge.

Same-directory Tangle commands serialize census, index reconciliation,
canonical mutation, and view publication with a project-scoped reconciliation
lease. A direct editor does not participate in that lease, so a file that changes
during the census causes a retry or an explicit concurrent-edit result rather than
a false clean snapshot; an edit after the command's validated boundary is observed
by the next command. The protocol does not claim an atomic multi-file snapshot
against arbitrary nonconforming writers.

Projection failure does not make a view authoritative. The command reports the
failure, and the next successful interaction repairs it from canonical Markdown.
A mutation's canonical acceptance boundary and its projection publication order
must be defined so a crash cannot make a generated page evidence that an
unaccepted mutation succeeded. Deterministic ordering and same-directory temporary
renames keep regenerated pages stable and avoid needless Git or editor churn.

### Coordination cost should follow coordination risk

The protocol should be progressively disclosed rather than promoted into the
core workflow wholesale. There are at least three useful operating levels:

1. A single writer edits canonical Markdown directly, follows the existing node
   mutation rules, and runs the ordinary acceptance gate. It does not create a
   proposal, declare a read set, manage a receipt, or acquire an integration
   lease.
2. Deliberately partitioned same-host or worktree execution may keep using the
   current claims, reserved IDs, exclusive write sets, handoffs, and serial
   integration. Disjoint work does not need to adopt change bundles merely
   because more than one agent exists.
3. Actors use sealed proposals and extended reconciliation when work is
   asynchronous, speculative, plausibly overlapping, independently hosted, or
   otherwise cannot safely rely on exclusive canonical write sets and an
   immediately available integrator.

These are escalation levels, not different graph contracts. Every accepted
result still ends as valid canonical Markdown and Git history. Tooling may
normalize direct edits, Git refs, and sealed bundles into one internal operation
model so validation and ingestion stay consistent. That internal uniformity must
not leak into a universal authoring burden: hashes, exact footprints, base bytes,
and mechanically derivable preconditions should be captured by tools whenever
possible, and an agent or human should supply extra metadata or a semantic
disposition only when the selected mode or an actual ambiguity requires it.

The full hash census and projection upkeep are tool behavior, not agent workflow.
They may run universally because they require no semantic choice or authored
metadata from the client. This is compatible with pay-for-what-you-use: ordinary
clients pay bounded local I/O for trustworthy derived answers, while only clients
that select concurrent intake pay the proposal and reconciliation protocol cost.

The skill should therefore retain only a compact routing rule: continue with the
ordinary workflow by default, and load a dedicated coordination or change-intake
reference when one of the escalation conditions appears. The detailed envelope,
operation, reconciliation, and receipt contracts belong in that conditional
reference and per-command help. Merely installing the capability must not make a
simple task consume or comply with all of its documentation.

## Proposed foundation: immutable change bundles

For the escalated intake path, introduce a transport-neutral **change bundle**.
A bundle is a non-authoritative proposal to transform one canonical graph
snapshot into another. Its default on-disk representation could be one uniquely
named file or directory under an explicitly non-node namespace such as
`.tangle/proposals/`; the same logical format could also arrive from a Git
ref, stdin, or an orchestration service. Direct canonical editing remains the
default when one writer can safely own and finish the mutation.

The important property is not the exact directory. It is that submitting a
sealed bundle creates a new unique object and never edits a canonical node or a
shared queue file. Exclusive creation prevents a naming race but does not by
itself make bytes immutable. A conforming transport must address a sealed bundle
by the digest of a defined canonical encoding and must reject replacement under
that identity. A Git blob or append-only service can provide that property; a
plain writable file needs an independently recorded digest before it is trusted.

### Scope and repository binding

A graph mutation cannot claim that implementation work is complete while leaving
the implementation behind on a worker branch. A bundle that only records a
knowledge change may contain graph operations alone. A bundle that transitions or
resolves a node based on repository work must also bind the exact non-graph change
it relies on: a Git tree or commit, or a content-addressed patch with its base and
result tree OIDs. The integration candidate applies and tests that repository
change together with the graph operations.

The acceptance unit is therefore a repository tree, not merely the `.tangle/`
subtree. Every resolving transition declares `repository_effect: none` or
`repository_effect: bound`; the latter names the repository payload digest. Policy
must reject `none` when the node's outcome requires code or artifact changes, and
must reject `bound` when the selected candidate does not contain the named result.
This keeps node evidence, generated artifacts, and implementation changes coherent
at the accepted commit without trying to infer the distinction from prose alone.

### Envelope

A minimal envelope needs:

```yaml
format: tangle-change/v1
proposal_id: 01j...
producer_id: worker-7        # optional, opaque, informational
run_id: optional-run-42      # optional, opaque, informational
created: 2026-09-14T16:00:00Z
base_git_oid: abc123...
payload_hash: sha256:...
intent: compound
repository_effect: bound
repository_payload_hash: sha256:...
```

The payload then contains operations, preconditions, evidence, and an optional
human summary. The proposal ID can be a sufficiently random UUID/ULID-like value;
the payload hash detects corruption and distinguishes proposal identity from
bytes. `tangle-change/v1` must define one canonical byte encoding. The digest
covers the domain separator, envelope fields other than `payload_hash`, and the
payload in that encoding; it never recursively covers its own field. A
producer-prefixed counter is not sufficient because producer identity is not
always stable or centrally registered. A digest is not authentication. A
surrounding transport may add signatures, authenticated channels, or policy when
its users need them, but Tangle neither requires nor verifies those mechanisms.

Asynchronous durability also requires the declared base to remain inspectable. A
transport either retains the base Git objects behind a durable proposal ref until
terminal disposition or embeds the target base bytes and other witnesses needed to
check every precondition. A bare OID that may disappear after garbage collection
is not a resumable contribution.

Drafts may remain private to an actor. Submission seals one immutable version.
Further thinking creates a new proposal with `supersedes_proposal`, which keeps
asynchronous intake append-only. Consumers should treat pending proposals as a
set, not a FIFO queue: dependency and conflict order matters, arrival order does
not.

### Operations

Operations should express graph intent rather than only a raw unified diff:

- `create`: propose a node with a local symbol, type, route, summary, body, and
  intended initial status;
- `amend`: propose a result against a node ID plus starting content hash and
  status;
- `transition`: couple an authoritative status-field change (or a legacy status
  path move) with the required body/frontmatter changes;
- `advance`: change a coordinating parent's frontier route with an expected old
  `next`;
- `supersede`: preserve an obsolete node and point it to its replacement;
- `retire`: explicitly abandon or deprecate a node while preserving its history;
- `restructure`: atomically split, consolidate, or reparent a set of outcomes;
- `compound`: make several operations indivisible, such as resolving a child and
  advancing its parent.

Canonical node deletion is not a normal operation: history is retained through a
disposition. An imported Git diff that deletes a node is classified `unknown`
unless it is proven to be one side of an identity-preserving move or translated
into an explicit retirement under repository policy. Repository payloads are
bound separately from graph operations, so a raw source-file deletion does not
pretend to be a graph disposition.

A graph operation may carry its full target base and result bytes or a patch, but
the semantic operation is what lets tooling reason about hazards. A bound
repository payload separately carries or durably references the exact repository
tree change. Timestamps and permanent IDs remain symbolic in a reconciliation plan
and are materialized only by an acceptance attempt, rather than authored
independently by every worker.

### Preconditions

Every operation names what the author believed:

- base Git OID;
- target node ID and content hash;
- expected status and, where relevant, expected `context_rev` and `next`;
- pinned dependency revisions read by the work;
- the complete graph and repository write set derived from the payload;
- the read set and graph predicates on which the conclusion depends;
- expected absence for a new canonical identity.

These are optimistic-concurrency checks. A mismatch never silently invalidates
the contribution; it changes its classification to `needs-rebase`,
`stale-context`, `overlap`, or another explicit state.

The existing base-hash claim fits this model as an early same-host exclusion
optimization. Correctness at acceptance still comes from checking the sealed
proposal's preconditions against the actual integration snapshot.

A producer may add explanatory read-set entries but may not weaken the footprint
derived from its operations and repository patch. If tooling cannot determine
whether a changed precondition was semantically read, the operation is
`needs-revision`; successful patch application and a structurally valid graph are
not proof that the original conclusion survives.

### Receipts and disposition

Proposals should not disappear when handled. Before building a commit, an
acceptance attempt chooses a globally unique `integration_id`. The candidate
tree contains a uniquely named immutable acceptance record with that ID, the
selected proposal IDs and digests, their dispositions, the generated canonical
IDs, and the plan hash. It deliberately does not contain the commit OID: a Git
commit cannot contain its own hash.

After the compare-and-swap succeeds, an immutable receipt records:

- integration ID;
- proposal ID and digest;
- disposition: `accepted`, `absorbed`, `redundant`, `superseded`, `rejected`, or
  `needs-revision`;
- canonical node IDs and commit OID produced, when the disposition created either;
- other proposals it was merged with or absorbed by;
- optional `integrator_id` asserted by the caller;
- checker and relevant test evidence;
- any manual semantic decision and its optional `decision_actor_id`.

Receipts preserve contribution provenance without polluting canonical node
frontmatter. `accepted`, `absorbed`, `redundant`, `superseded`, and `rejected` are
terminal; `needs-revision` is nonterminal and a revised contribution receives a
new proposal ID linked to the old one. At most one terminal disposition is valid
for a proposal. Conflicting receipts are a reconciliation error, never
last-writer-wins state.

The acceptance record, for example
`.tangle/acceptances/<integration_id>.yaml`, closes the crash window between
updating the canonical ref and publishing receipts. Every terminal disposition,
including rejection without a graph change, passes through the same serialized
acceptance path and appears in one of these records; a rejection may therefore
produce a metadata-only canonical commit. A retry first searches the canonical
history for the proposal digest or integration ID. If the terminal commit exists,
it reconstructs or republishes the missing receipt instead of applying the
proposal again. A receipt written before the ref update is only provisional and
grants no terminal status.

Whether proposals and receipts remain in the working tree, live in dedicated Git
refs, or are compacted after a retention horizon is a storage-policy question.
The logical contract should not depend on the transport. If they are ordinary
tracked files, terminal handling should add a receipt rather than rewrite a
shared manifest. The canonical acceptance record is retained for at least as long
as any receipt or proposal that depends on it. Garbage collection must be explicit
and must not erase the only record needed to explain an accepted mapping.

## Reconciliation as a reduction pipeline

An extended reconciler can operate on commits, working-tree bundles, or explicit
proposal IDs through the same stages.

### 1. Collect and verify

First run the universal canonical-store hash census and reconcile the sidecar and
Markdown views. Then read immutable bundles, verify their digest, resolve their
bases, and derive their repository and graph footprints against that reconciled
snapshot. Consult both receipts and canonical acceptance records: an
accepted-but-unreceipted proposal is receipt-recovery work, not pending work. A
malformed or unverifiable proposal remains separate from graph validity. Optional
actor metadata does not affect either classification; any authentication or
authorization check happens outside Tangle.

### 2. Normalize exact equivalence

Identical operations or identical proposed result bytes are mechanically
detectable. Keep every origin in the receipt, choose one representative, and
classify the rest as `absorbed` rather than creating duplicate nodes.

### 3. Build an overlap graph

Connect proposals that share any of:

- canonical target identity, authoritative status field, or legacy status path;
- parent `next` or another singleton field;
- dependency whose revision one changes and another consumes;
- proposed local-symbol mapping;
- derived read/write path or graph predicate;
- plausible existing owner or near-duplicate outcome.

The first five are deterministic. Semantic similarity, `tangle similar`,
digests, and clusters may nominate the last kind, but must stay advisory. A low
similarity score can never prove independence.

### 4. Classify components

Useful classes include:

- `apparently-disjoint`: derived footprints do not overlap, pending combined
  validation;
- `commutes`: the selected union has order-independent materialized content and
  passes full candidate validation;
- `same-result`: different contributions produce the same result;
- `clean-rebase`: changed preconditions are proven outside the machine-derived
  structural footprint, an explicit decision confirms that no declared semantic
  read is affected, and replay produces the same checked result;
- `stale-context`: a consumed dependency revision changed;
- `same-node-overlap`: multiple proposals alter one node;
- `frontier-contention`: proposals compete for one parent's `next`;
- `identity-collision`: canonical or proposal-local identity maps collide;
- `possible-redundancy`: different identities appear to own the same outcome;
- `semantic-conflict`: conclusions or requested states cannot both be true;
- `boundary-change`: split, consolidation, reparenting, or supersession is
  required;
- `unknown`: tooling lacks enough evidence to accept automatically.

`unknown` is a successful safety result, not a parser failure. A structurally
clean patch replay is not enough to upgrade `needs-revision` to `clean-rebase`.

### 5. Construct a hypothetical repository tree

Apply only selected or provably replayable operations and their bound repository
payloads to a scratch worktree or temporary tree. Keep new IDs and acceptance
timestamps as typed symbolic values in the plan. To exercise the existing checker,
derive deterministic, explicitly noncanonical validation IDs from the project UID,
proposal digest, and local symbol, and use one valid but noncanonical validation
timestamp. Derive the index and views from that candidate Markdown, run
`tangle check`, and run the tests required by the full repository change.
Recompute stale consumers against this combined candidate, not only against each
head independently. Acceptance rematerializes the real identity spelling and
timestamp and reruns the gates on the exact candidate it may commit.

This catches the important case where every branch is internally valid but their
union is not. Only after this stage may an `apparently-disjoint` component become
`commutes`. If applying the selected set in different topological orders changes
the symbolic candidate or its predicates, it does not commute. The initial pass
contains only mechanically eligible proposals; after stage 6 resolves an ambiguous
component, the resulting selection returns through this stage before acceptance.

### 6. Require semantic dispositions

Automation can combine commuting operations and exact duplicates. It should not
silently choose between competing outcomes. An integrator given an explicit
decision can:

- choose one proposal;
- synthesize a replacement proposal that absorbs several;
- retain both after proving independent outcomes;
- turn a conflict into a new unsettled `THO` or task when it meets admission;
- request revision with a specific failed precondition;
- reject or defer with a reason.

Restructuring should always be represented as an explicit compound operation.
For a split, the receipt maps one prior owner to several new owners and rewrites
or preserves backlinks deliberately. For consolidation, one strong owner
continues and the others receive durable dispositions. A generic merge tool
should not infer either solely from file size, session boundaries, or agent
count.

### 7. Serialize acceptance

Acquire a repository integration lease. Read the expected Git head, order selected
proposals and their local symbols by a specified stable key, and generate each new
lowercase canonical ID under the resolved collision-resistant identity contract.
Materialize one real host-clock timestamp for the attempt, create the acceptance
record and one coherent repository commit, and update the ref with compare-and-swap
semantics. The plan hash covers the symbolic plan and expected head, not the
attempt's timestamps, generated canonical IDs, or commit OID.

If the head moved, publish neither terminal receipts nor canonical mappings. The
attempt's candidate tree is invalid, and reconciliation restarts against the
winning head. A collision-resistant ID may remain the attempt's deterministic
candidate, but it grants no canonical identity before the CAS succeeds. Legacy
same-host numeric reservations remain compatibility state and are not evidence of
a cross-host canonical allocation.

After a successful ref update, publish receipts that point from each proposal and
the acceptance record's integration ID to the resulting commit OID. A crash before
receipt publication is recovered from the acceptance record as described above.
No separate receipt-store race can choose a different terminal result because the
canonical acceptance history, not receipt arrival order, owns disposition.

Same-host SQLite can implement the lease. Across hosts, a server-side lock or an
atomic Git ref update can provide the compare-and-swap boundary. The proposal
format should not assume either deployment. Tangle does not establish or
enforce who may perform the ref update or provide a semantic decision. Those
constraints, when wanted, belong to the surrounding environment.

## Scenario sketches

### Several agents in one working directory

Direct canonical edits and Git staging remain unsafe because all actors share
both paths and index state when they write concurrently. The simplest workflow
may serialize those edits and retain the ordinary direct path. If the actors must
contribute asynchronously, each instead submits a uniquely named sealed bundle.
Submission performs only exclusive creation. Any actor may continue working and
submit more bundles; no actor rewrites another's proposal.

Every project-scoped graph command first hashes and reconciles the complete
canonical store, so a direct point edit made by a human or another tool before
submission or integration is part of the actual base rather than invisible
sidecar drift. An integration pass then serializes canonical changes. If no
coordinator exists, the first actor to acquire
the integration lease may become the temporary integrator. The lease conveys no
permission or trust; it only prevents another conforming integrator from accepting
concurrently. Ambiguous components stay pending until an explicit decision is
supplied. The successful mutation refreshes the derived index and Markdown views;
no producer authors either.

### Several worktrees on one host

Existing sidecar allocation and claims remain useful for deliberately assigned
direct edits. Change bundles add a safer mode for speculative or overlapping
work. The reconciler can accept Git refs directly, so a worker need not copy
files into a central queue before its branch is inspectable.

The integrator unions bundles from the selected refs, then evaluates them against
the current canonical head. A worktree's old snapshot is treated as a declared
base, never as global truth.

### Several hosts

Local leases cannot coordinate them. Each host can still create globally unique
sealed proposals. Git transport or an orchestration service collects them. Only
the final ref update needs cross-host serialization. New lowercase canonical node
IDs are generated collision-resistantly at admission and become authoritative only
for the compare-and-swap winner. No shared numeric allocator is required for the
new identity format; legacy numeric creation still needs the existing allocator or
explicitly disjoint ranges.

### Two agents discover the same missing work

If their payloads are exactly equivalent, one accepted node maps both proposals
in its receipt. If they differ, similarity can surface `possible-redundancy`; an
integrator decides whether to synthesize one node, keep independent nodes, or
preserve an unresolved question. Neither producer loses attribution, and neither
proposal ID becomes the canonical node ID.

### Two agents advance the same node

Both amendments name the starting node hash. The overlap graph places them in one
component. Disjoint textual hunks are not enough for automatic acceptance: an
edit to evidence and an edit to the conclusion may interact semantically.
Exact/safely replayable changes may combine; otherwise the integrator authors a
replacement proposal or asks for revision.

### Execution reveals a different boundary

A worker can submit a compound restructure proposal instead of directly creating
several canonical nodes. The proposal names the evidence for independent
resumability and the old owner's mapping. Another worker may independently
propose consolidation. The reconciler classifies both as one boundary-change
component, and no partial split or backlink rewrite becomes authoritative before
the whole component passes validation.

### A worker disappears

An expired claim releases exclusion, but its sealed proposals remain readable.
Another actor can resume from the recorded base, operations, and evidence. An
unsealed local draft is intentionally not durable; orchestration that needs crash
recovery should seal coherent increments rather than exposing mutable canonical
WIP.

## Possible command surface

The names are illustrative; the data model matters more than the verbs.

```text
tangle change submit --producer ID --base REF --file CHANGE
tangle change pending [--ref REF ...]
tangle change inspect PROPOSAL
tangle reconcile --base REF --proposal ID ... --head REF ...
tangle integrate --plan PLAN --dry-run
tangle change decide PROPOSAL --as DISPOSITION --output DECISION
tangle integrate --plan PLAN --decision DECISION ... --apply --expect-head OID
tangle change receipt PROPOSAL
```

`reconcile` should remain read-only and deterministic. `integrate --dry-run`
should validate the symbolic candidate and may show a clearly noncanonical
illustrative materialization without changing the canonical ref. `--apply`
materializes attempt-local IDs and timestamps, reruns the full checker and required
tests on those exact bytes, and refuses unresolved components, stale plan hashes,
or a moved head. Machine-readable output needs stable action and conflict codes so
both a rich orchestrator and a shell user can drive the same protocol. A decision
file is non-authoritative input to integration; it cannot create a terminal
disposition or receipt without the serialized acceptance step.

There is also room to extend the current claim primitive from a node key to a
bundle or named write-set lease, but that remains an optimization. A writer that
never claims must still be unable to bypass acceptance preconditions.

## Invariants worth preserving

1. Canonical Markdown and Git remain the durable authority for accepted graph
   knowledge.
2. Canonical nodes have stable paths and immutable lowercase logical identities;
   their IDs use a 128-bit, 26-character Crockford Base32 payload, and content
   hashes identify revisions, not nodes.
3. Every project-scoped graph command hashes the complete canonical node store
   before answering, so direct point edits, additions, and deletions reconcile
   automatically; repository-independent help and version operations need no vault.
4. Derived SQLite state and generated Markdown views can be lost without losing
   accepted knowledge or pending durable proposals.
5. Clients never maintain indexes, status pages, summary aliases, or projection
   symlinks; Tangle regenerates every supported projection from canonical
   Markdown.
6. A committed immutable project UID supplies cross-clone authority. Lowercase
   project aliases and collision-aware terminal abbreviations are mutable
   presentation and local lookup state; neither replaces a full canonical ID.
7. Local wikilinks remain meaningful local-vault links. Cross-project references
   use a distinct durable Tangle grammar and may gain Obsidian links only
   through a generated projection.
8. No mutable global queue manifest is required for submission.
9. One sealed proposal has immutable bytes and a globally unique identity.
10. Actor and run fields are optional, opaque, informational metadata that never
   affect acceptance.
11. An integration lease grants exclusion among conforming clients and conveys no
   permission, identity, or trust.
12. Permanent node identity is assigned at admission, not speculative creation.
13. A compound graph and bound repository transition is accepted entirely or not
   at all.
14. Acceptance checks the proposal's base assumptions against the actual
   integration snapshot.
15. Every terminal disposition has one idempotent receipt, and every accepted
    commit carries enough non-self-referential data to recover a missing receipt.
16. Semantic redundancy and node-boundary changes are surfaced for judgment;
    advisory similarity never decides them.
17. The plain `tangle check` and the gates required by the bound repository
    change pass at every completed integration boundary.
18. Semantic ambiguity requires an explicit decision, but Tangle neither
    authenticates its source nor judges who may provide it.
19. Canonical nodes are retired with durable dispositions rather than deleted.

## What not to build first

- A CRDT for canonical Markdown. It solves concurrent bytes, not graph meaning.
- A shared `queue.md`. It recreates the merge hotspot removed from
  `index-map.md`.
- Permanent `agent:` ownership in node frontmatter. Claims expire and agents can
  hand off the same outcome.
- Automatic semantic deduplication. False consolidation can erase an independent
  outcome.
- A sidecar-only durable queue. Sidecar loss is currently allowed and cross-host
  visibility is not guaranteed.
- Client-maintained indexes, aliases, or status projections. They duplicate
  canonical facts and make correctness depend on every caller remembering
  bookkeeping.
- A content hash as mutable node identity. It turns an ordinary edit into an
  identity change instead of a revision.
- A project alias as durable authority. Human names can be renamed or collide;
  the committed project UID owns identity.
- Cross-project references disguised as local wikilinks. A projection may make
  them convenient, but the canonical reference must survive without that view.
- Blind application of `git merge` results followed only by repair. The tool
  should validate a hypothetical union before it becomes the accepted graph.

## Incremental experiments

The smallest useful experiments are narrower than a complete orchestration
system:

1. Define and schema-test 128-bit lowercase Crockford Base32 project and node
   identity, collision-aware human terminal abbreviations, local and qualified
   reference grammar, the stable canonical path, compatibility with uppercase
   numeric IDs, and the distinction between logical identity and content hash.
2. Re-run the stationary-storage comparison with the derived sidecar, a full-file
   hash census, point edits with preserved metadata, deterministic Markdown view
   pages, sidecar loss, case-only migration, and an optional symlink backend.
3. Implement and fault-test per-command full-store hashing, transactional index
   reconciliation, and atomic projection regeneration before proposal intake
   relies on the resulting snapshot.
4. Define and schema-test the canonical proposal encoding and digest boundary,
   with `create`, `amend`, and `compound` operations.
5. Add a read-only adapter that turns one or more Git refs into those logical
   operations, classifying any semantically ambiguous diff as `unknown` and
   preserving today's `reconcile` output as a compatibility view.
6. Extend reconciliation fixtures with prohibited node deletion, an
   identity-preserving move, exact duplicate work under different IDs, concurrent
   parent advances, cross-node parent cycles, and a split-versus-amend case.
7. Build a scratch-tree validator that applies bound code and artifact changes as
   well as graph operations, reports whether the selected set passes
   `tangle check` and its required gates, and never writes the current worktree.
8. Test read/write-footprint derivation and prove that a clean textual rebase with
   an uncertain semantic read remains `needs-revision`.
9. Test stable proposal ordering, late collision-resistant ID generation, and
   symbolic plan hashing under concurrent and arbitrarily ordered submission.
10. Test receipt idempotency by crashing immediately after a successful canonical
   ref update and recovering the receipt from the acceptance record.
11. Add a compare-and-swap integration prototype and deliberately race integrators
   carrying distinct, duplicated, and absent optional actor metadata.
12. Measure full-census latency and bytes read as the vault grows, projection
   rewrite frequency, proposal accumulation, false-positive overlap components,
   human or coordinator resolution effort, and recovery after a producer
   disappears.

The key falsification test is not merely that disjoint files merge. It is that a
mixed workload of additions, amendments, dependency bumps, redundant outcomes,
and restructuring proposals can be collected in arbitrary order; that all
mechanically safe subsets produce the same canonical candidate; and that every
unsafe or uncertain subset stops with enough evidence for a new integrator to
continue without reconstructing the original agent topology.
