# Change-intake reference

Load this reference before submitting, inspecting, reconciling, deciding, or
integrating an asynchronous graph contribution. It is an opt-in path: ordinary
single-writer work remains direct canonical Markdown editing. Deliberately
partitioned same-host or worktree work may continue to use assigned write sets,
claims, and serial integration. Use change intake only when work is asynchronous,
speculative, plausibly overlapping, independently hosted, or cannot safely rely
on exclusive canonical write sets and an immediately available integrator.

## Authority and identity

Canonical Markdown and accepted Git history remain authoritative. A change is a
non-authoritative, immutable proposal; a pending set is not a FIFO queue and no
proposal changes a canonical node before serialized acceptance.

`braintree-change/v1` is the only initial envelope format. Its canonical bytes
are UTF-8 JSON with recursively sorted object keys, no insignificant whitespace,
LF line endings in embedded text, and a trailing LF. Its digest is
`sha256("braintree-change/v1\\0" || canonical_bytes_without_payload_hash)`;
`payload_hash` is that digest and is never recursively covered. A proposal ID is
a globally unique 128-bit lowercase Crockford payload prefixed `chg-`; it is not
a node ID, actor identity, or authentication claim. `producer_id` and `run_id`
are optional opaque metadata covered by the digest but confer no authority.

New canonical IDs are `tas-`, `tho-`, `def-`, `dec-`, `idx-`, or `fbk-` followed
by exactly 26 lowercase Crockford Base32 characters matching
`[0-7][0-9a-hjkmnp-tv-z]{25}`. Acceptance generates the 128-bit payload from
cryptographic randomness; it materializes no permanent node ID in a proposal.
Legacy uppercase numeric IDs stay readable during the migration window, but all
new stored IDs, filenames, and references use the lowercase spelling.

Every vault commits one immutable `prj-` UID with the same payload grammar. It
identifies the project across clones and is distinct from any same-host local
coordination key. An unqualified ID means this project. `alias:node` is accepted only as local
input or display shorthand and expands to the registered `prj-` UID in durable
artifacts. Cross-project references use `braintree://prj-.../node/...`, never an
Obsidian wikilink; an unregistered target remains visible and unresolved.

Terminal displays may abbreviate as a type plus at least eight payload characters
and `...`, lengthening deterministically until unique in that result. Full IDs are
mandatory in Markdown, proposals, plans, receipts, logs used as evidence, and
structured output; an abbreviation is never accepted input or stored identity.

## Canonical store and views

The stationary canonical-store format keeps an immutable creation label in the
basename and makes status an authoritative node-content field. A content hash is
an exact-byte version and optimistic precondition, never logical identity. A
legacy status-directory move is normalized as one identity-preserving transition
until migrated.

Before every project-scoped read or mutation, Braintree acquires its local
reconciliation lease, enumerates every canonical node, hashes exact bytes,
transactionally reconciles new, changed, and vanished paths into derived state,
then answers from that snapshot. A direct edit observed during census retries or
returns a concurrent-edit result. Mutation commands publish their known post-write
delta instead of performing a redundant second census. Global help, version, and
installation commands are vault-independent.

Braintree regenerates deterministic, disposable Markdown views for status, area,
priority, recent activity, and registered external projects, using canonical
summaries as display text. Views and optional symlinks are excluded from discovery
and authority: missing or corrupt views are repaired on the next successful
interaction and cannot hide canonical Markdown. Canonical acceptance precedes view
publication, so a failed projection never proves an unaccepted mutation.

## Proposal contents and local scope

A sealed proposal contains its format, proposal ID, optional actor/run metadata,
base witness, canonical payload and digest, intent, graph operations,
`repository_effect`, evidence, and derived read/write footprints. The base witness
is either durable Git objects retained until terminal disposition or embedded bytes
needed to check every precondition. A bare collectible OID is insufficient.

Supported v1 graph operations are `create`, `amend`, `transition`, `advance`,
`supersede`, `retire`, `restructure`, and indivisible `compound`. A creation uses
a proposal-local symbol; references to it use `proposal_id#symbol` until
acceptance maps it to a permanent ID. Canonical node deletion is not an operation:
an unexplained deletion is `unknown` unless normalized as an identity-preserving
move or explicit retirement.

Preconditions include the base, target IDs and exact content hashes, expected
status, `context_rev` and `next` where relevant, consumed dependency revisions,
expected absence for new identity, and all derived graph/repository footprints.
Producer-supplied explanatory reads may add context but cannot narrow a derived
footprint. A mismatch produces an explicit classification, never silent replay.

The local MVP accepts graph-only operations with `repository_effect: none`.
It rejects or defers a task resolution whose outcome requires unbound code or
artifact changes. Later worktree proposals use `repository_effect: bound` with an
exact commit, tree, or content-addressed patch binding and validate that payload
with the graph candidate; v1 local intake never accepts an unbound repository
claim.

## Pending state, reconciliation, and decisions

Submission exclusively creates a content-addressed sealed object and rejects a
different replacement under the same identity. Revising a draft creates a new
proposal linked by `supersedes_proposal`; it never edits the old one. Pending
proposals remain inspectable until terminal disposition. Exact-equivalent
proposals are retained as origins and may be `absorbed` into one representative.

Reconciliation is read-only and deterministic: verify envelopes and witnesses;
normalize exact equivalence; derive overlap components; classify each component;
construct and validate a symbolic candidate; then request explicit decisions for
ambiguity. Classes include `apparently-disjoint`, `commutes`, `same-result`,
`clean-rebase`, `stale-context`, `same-node-overlap`, `frontier-contention`,
`identity-collision`, `possible-redundancy`, `semantic-conflict`,
`boundary-change`, and `unknown`. Similarity may nominate a conflict but never
proves independence. `unknown` is a successful safety result.

Only exact duplicates and proven commuting operations may proceed automatically.
An integrator must explicitly choose, synthesize a replacement, retain independent
outcomes with evidence, request revision, reject/defer with a reason, or create a
new admitted question/task. A decision file is non-authoritative input and cannot
produce a terminal disposition by itself.

The candidate applies selected operations and any bound repository payload to a
scratch tree, uses deterministic noncanonical validation IDs and timestamp,
rebuilds derived views, runs `braintree check`, recomputes stale consumers against
the combined candidate, and runs the required repository gates. Different valid
orders that yield different candidate bytes do not commute.

## Acceptance, recovery, and retention

Integration serializes on the project lease and an expected-head compare-and-swap.
It rereads the canonical census and all preconditions, orders selected proposals
and symbols by stable key, materializes one host-clock timestamp and permanent
IDs, reruns the exact candidate gates, and writes one immutable acceptance record
with its integration ID, expected head, plan hash, selected proposal digests,
dispositions, generated ID mappings, and evidence. A moved head publishes no
terminal receipt or mapping and restarts reconciliation.

After the compare-and-swap succeeds, immutable receipts record the integration
ID, proposal digest, terminal disposition, produced canonical IDs and commit when
any, absorbed origins, optional integrator/decision actors, and checker/test
evidence. Terminal dispositions are `accepted`, `absorbed`, `redundant`,
`superseded`, and `rejected`; `needs-revision` remains nonterminal and its revision
uses a new proposal ID. Conflicting terminal receipts are a reconciliation error.

On retry, search canonical history for the integration ID or proposal digest.
When the commit exists, reconstruct or republish a missing receipt rather than
applying the proposal twice. The acceptance record is retained at least as long as
any dependent proposal or receipt. Compaction or garbage collection is explicit
storage policy and must not erase the only explanation of an accepted mapping.

## Command boundary and compatibility

The intended commands are `braintree change submit`, `change pending`, `change
inspect`, `change decide`, `change receipt`, `reconcile --proposal`, and
`integrate --dry-run|--apply --expect-head`. Each command owns exact operands,
output fields, error codes, and hazards in its per-command help. `reconcile` and
`integrate --dry-run` are read-only; `--apply` refuses unresolved components,
stale plan hashes, or moved heads.

Ordinary node commands retain their direct-Markdown behavior. The existing
read-only `braintree reconcile --base/--head` view stays available as a bounded
compatibility view while proposal reconciliation is added; selecting this protocol
is the only trigger for its authoring burden. Unknown or downgraded envelope
versions are rejected.

Required fixtures cover identity casing and canonicalization, clone-stable project
scope, local and qualified references, preserved direct-edit metadata, missing or
corrupt projections, malformed envelopes, unsupported operations, absent actor
metadata, stale bases, and unknown or downgraded versions.
