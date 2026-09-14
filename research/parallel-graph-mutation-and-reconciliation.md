# Parallel graph mutation and reconciliation

Status: exploratory research. This document describes a possible foundation; it
does not change the Braintree contract.

Any implementation of this foundation should be pay-for-what-you-use. Ordinary
single-writer work remains direct Markdown editing under the existing Braintree
contract. The proposal, reconciliation, and receipt machinery is an opt-in
coordination path for asynchronous, overlapping, or independently hosted work,
not a new checklist imposed on every graph mutation. An implementation may use
the same normalized ingestion model internally for all changes, provided the
ordinary path does not require an agent to author or reason about that machinery.

## Problem

Braintree deliberately makes each node a directly editable Markdown file. That
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
operating discipline, but it assumes an orchestration shape that Braintree cannot
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

### Same-host identity and exclusion

The external SQLite sidecar is keyed by Git's common directory, so all local
worktrees share atomic ID sequences and node claims. `braintree allocate` burns
IDs rather than risking reuse, and `braintree node record` reserves before using
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

`braintree check` validates the canonical graph after edits. It detects duplicate
identities, invalid routes, stale pins, and lifecycle errors. The
`--allow-pending-advance` exception precisely represents one known multi-writer
transient without weakening unrelated checks.

This is an important pattern: name a bounded transient, make it explicit, and
keep the ordinary acceptance gate strict.

### Read-only reconciliation planning

`braintree reconcile --base ... --head ...` reads Git snapshots and reports:

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
2. **Identity conflict:** two paths claim the same Braintree ID.
3. **Invariant conflict:** the combined files violate routing, lifecycle,
   dependency, or frontier rules.
4. **Meaning conflict:** two valid nodes own the same outcome, two edits express
   incompatible conclusions, or execution reveals a different node boundary.

Git handles the first incompletely. `braintree check` and today's reconciler
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
integration lease establishes exclusion among conforming clients only. Braintree
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

Braintree preserves and exposes these caller-supplied values and includes them in
the sealed object's digest. It does not require them, authenticate them, require
uniqueness or stability, infer a role or permission from them, or use them to
accept or reject an operation. They are asserted provenance metadata for users and
external systems to interpret. Proposal and integration identities remain unique
even when every actor field is absent, duplicated, or misleading.

### Permanent node IDs should be allocated late

Cross-host proposals cannot safely share a local sequence. More importantly,
allocating canonical IDs while ideas are still redundant or subject to
consolidation creates needless burns and encourages proposal identity to become
graph identity.

A new-node contribution can use a proposal-scoped symbol, addressed globally as
`proposal_id#symbol`. The integrator allocates the permanent
`TAS`/`THO`/`DEF`/`DEC`/`FBK` ID only when it admits the node, then records the
mapping in the acceptance record and receipt. References among nodes created by
one bundle use proposal-scoped symbols until that mapping is fixed.

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
`.braintree/proposals/`; the same logical format could also arrive from a Git
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

The acceptance unit is therefore a repository tree, not merely the `.braintree/`
subtree. Every resolving transition declares `repository_effect: none` or
`repository_effect: bound`; the latter names the repository payload digest. Policy
must reject `none` when the node's outcome requires code or artifact changes, and
must reject `bound` when the selected candidate does not contain the named result.
This keeps node evidence, generated artifacts, and implementation changes coherent
at the accepted commit without trying to infer the distinction from prose alone.

### Envelope

A minimal envelope needs:

```yaml
format: braintree-change/v1
proposal_id: 01J...
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
bytes. `braintree-change/v1` must define one canonical byte encoding. The digest
covers the domain separator, envelope fields other than `payload_hash`, and the
payload in that encoding; it never recursively covers its own field. A
producer-prefixed counter is not sufficient because producer identity is not
always stable or centrally registered. A digest is not authentication. A
surrounding transport may add signatures, authenticated channels, or policy when
its users need them, but Braintree neither requires nor verifies those mechanisms.

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
- `transition`: couple a status move with the required body/frontmatter changes;
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
selected proposal IDs and digests, their dispositions, the allocated canonical
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
`.braintree/acceptances/<integration_id>.yaml`, closes the crash window between
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

Read immutable bundles, verify their digest, resolve their bases, and derive their
repository and graph footprints. Consult both receipts and canonical acceptance
records: an accepted-but-unreceipted proposal is receipt-recovery work, not pending
work. A malformed or unverifiable proposal remains separate from graph validity.
Optional actor metadata does not affect either classification; any authentication
or authorization check happens outside Braintree.

### 2. Normalize exact equivalence

Identical operations or identical proposed result bytes are mechanically
detectable. Keep every origin in the receipt, choose one representative, and
classify the rest as `absorbed` rather than creating duplicate nodes.

### 3. Build an overlap graph

Connect proposals that share any of:

- canonical target identity or status path;
- parent `next` or another singleton field;
- dependency whose revision one changes and another consumes;
- proposed local-symbol mapping;
- derived read/write path or graph predicate;
- plausible existing owner or near-duplicate outcome.

The first five are deterministic. Semantic similarity, `braintree similar`,
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
derive tentative IDs from the expected head and stable proposal order, and use one
valid but explicitly noncanonical validation timestamp. Derive the index from that
candidate Markdown, run `braintree check`, and run the tests required by the full
repository change. Recompute stale consumers against this combined candidate, not
only against each head independently. Acceptance rematerializes the real timestamp
and reruns the gates on the exact candidate it may commit.

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
proposals and their local symbols by a specified stable key, and allocate each
prefix from the first unused canonical number visible at that head. Materialize
one real host-clock timestamp for the attempt, create the acceptance record and one
coherent repository commit, and update the ref with compare-and-swap semantics.
The plan hash covers the symbolic plan and expected head, not the attempt's
timestamps, allocated IDs, or commit OID.

If the head moved, publish neither terminal receipts nor canonical mappings. The
attempt's ID allocation and candidate tree are invalid, and reconciliation restarts
against the winning head. This optimistic rule is also the cross-host allocation
protocol: two hosts may tentatively choose the same next number, but only the CAS
winner makes its mapping canonical; the loser recomputes from the new head. A
same-host `braintree allocate` reservation is not evidence of a cross-host
canonical allocation.

After a successful ref update, publish receipts that point from each proposal and
the acceptance record's integration ID to the resulting commit OID. A crash before
receipt publication is recovered from the acceptance record as described above.
No separate receipt-store race can choose a different terminal result because the
canonical acceptance history, not receipt arrival order, owns disposition.

Same-host SQLite can implement the lease. Across hosts, a server-side lock or an
atomic Git ref update can provide the compare-and-swap boundary. The proposal
format should not assume either deployment. Braintree does not establish or
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

An integration pass serializes canonical changes. If no coordinator exists, the
first actor to acquire the integration lease may become the temporary integrator.
The lease conveys no permission or trust; it only prevents another conforming
integrator from accepting concurrently. Ambiguous components stay pending until an
explicit decision is supplied.

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
the final ref update needs cross-host serialization. Canonical node numbers are
tentatively derived from the expected head in stable proposal order and become
allocated only for the compare-and-swap winner. A deployment must not mix this
mode with speculative direct canonical ID allocation on independent hosts unless a
central allocator or explicitly disjoint ranges prevent an unseen direct edit from
using the same ID.

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
braintree change submit --producer ID --base REF --file CHANGE
braintree change pending [--ref REF ...]
braintree change inspect PROPOSAL
braintree reconcile --base REF --proposal ID ... --head REF ...
braintree integrate --plan PLAN --dry-run
braintree change decide PROPOSAL --as DISPOSITION --output DECISION
braintree integrate --plan PLAN --decision DECISION ... --apply --expect-head OID
braintree change receipt PROPOSAL
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
2. Derived SQLite state can be lost without losing accepted knowledge or pending
   durable proposals.
3. No mutable global queue manifest is required for submission.
4. One sealed proposal has immutable bytes and a globally unique identity.
5. Actor and run fields are optional, opaque, informational metadata that never
   affect acceptance.
6. An integration lease grants exclusion among conforming clients and conveys no
   permission, identity, or trust.
7. Permanent node identity is assigned at admission, not speculative creation.
8. A compound graph and bound repository transition is accepted entirely or not
   at all.
9. Acceptance checks the proposal's base assumptions against the actual
   integration snapshot.
10. Every terminal disposition has one idempotent receipt, and every accepted
    commit carries enough non-self-referential data to recover a missing receipt.
11. Semantic redundancy and node-boundary changes are surfaced for judgment;
    advisory similarity never decides them.
12. The plain `braintree check` and the gates required by the bound repository
    change pass at every completed integration boundary.
13. Semantic ambiguity requires an explicit decision, but Braintree neither
    authenticates its source nor judges who may provide it.
14. Canonical nodes are retired with durable dispositions rather than deleted.

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
- Blind application of `git merge` results followed only by repair. The tool
  should validate a hypothetical union before it becomes the accepted graph.

## Incremental experiments

The smallest useful experiments are narrower than a complete orchestration
system:

1. Define and schema-test the canonical proposal encoding and digest boundary,
   with `create`, `amend`, and `compound` operations.
2. Add a read-only adapter that turns one or more Git refs into those logical
   operations, classifying any semantically ambiguous diff as `unknown` and
   preserving today's `reconcile` output as a compatibility view.
3. Extend reconciliation fixtures with prohibited node deletion, an
   identity-preserving move, exact duplicate work under different IDs, concurrent
   parent advances, cross-node parent cycles, and a split-versus-amend case.
4. Build a scratch-tree validator that applies bound code and artifact changes as
   well as graph operations, reports whether the selected set passes
   `braintree check` and its required gates, and never writes the current worktree.
5. Test read/write-footprint derivation and prove that a clean textual rebase with
   an uncertain semantic read remains `needs-revision`.
6. Test stable proposal ordering, late canonical ID allocation, and symbolic plan
   hashing under concurrent and arbitrarily ordered submission.
7. Test receipt idempotency by crashing immediately after a successful canonical
   ref update and recovering the receipt from the acceptance record.
8. Add a compare-and-swap integration prototype and deliberately race integrators
   carrying distinct, duplicated, and absent optional actor metadata.
9. Measure proposal accumulation, false-positive overlap components, human or
   coordinator resolution effort, and recovery after a producer disappears.

The key falsification test is not merely that disjoint files merge. It is that a
mixed workload of additions, amendments, dependency bumps, redundant outcomes,
and restructuring proposals can be collected in arbitrary order; that all
mechanically safe subsets produce the same canonical candidate; and that every
unsafe or uncertain subset stops with enough evidence for a new integrator to
continue without reconstructing the original agent topology.
