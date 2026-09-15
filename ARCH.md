# Tangle: a small core with useful layers

## Recommendation

Build Tangle around **a Markdown graph interpreter and a deterministic work
resolver**. Everything else should consume their results: agent packets, human
documents, search, planning assistance, and concurrent-work coordination.

The essential product is small:

1. Keep durable intent, decisions, and unfinished work in readable files.
2. Answer what can happen next, with the evidence behind that answer.
3. Detect broken structure and stale assumptions.
4. Help record a result without making the author perform bookkeeping.

I would keep typed Python for the first replacement, with a prepared runtime and
no package resolution during ordinary commands. The complexity here comes mainly
from accumulated responsibilities and contracts, not Python. A Go implementation
would be reasonable if distributing a standalone executable became the overriding
requirement; it would still need the same architectural cuts. Keep Python's
optional model dependencies in a separately installed search tool either way.

This is an architecture proposal, not an adopted change to the skill or a promise
to implement every existing capability again.

## What the current size actually contains

Inspection of `src/tangle/*.py` found **23,867 physical lines**, including comments
and blank lines. A reproducible grouping by module name gives:

| Responsibility | Lines | Share |
|---|---:|---:|
| `*benchmark*`, `memory_*`, and `storage_comparison.py` | 11,443 | 48% |
| `clustering`, `provider`, `semantic`, and `reduction` | 1,612 | 7% |
| `cli`, `main`, `help`, `graph_check`, and `index` | 6,397 | 27% |
| Remaining storage, authoring, views, identity, coordination, etc. | 4,415 | 18% |

These are responsibility estimates, not a claim that every line in a group can
be deleted. Nevertheless, almost half the package is research infrastructure.
Separating it would leave roughly 12.4 KLOC before simplifying the actual product.
Moving files makes the runtime smaller; it does not by itself reduce maintenance.

The more consequential coupling is visible in a few places:

- [`main.py`](src/tangle/main.py) eagerly imports research modules and dispatches
  benchmarking alongside routine graph operations. It also arranges index upkeep
  and generated-view publication around commands.
- [`index.py`](src/tangle/index.py), at 2,485 lines, includes its own Markdown
  interpretation, SQLite maintenance, routing, execution packets, ranking,
  manifests, and Git reconciliation.
- [`graph_check.py`](src/tangle/graph_check.py) owns both parsing primitives and
  validation; `index.py` shares some of those primitives but also defines separate
  frontmatter and edge parsing. [`store.py`](src/tangle/store.py) separately reads
  status. There is no single parsed document all these consumers share.
- [`sidecar.py`](src/tangle/sidecar.py) combines live leases and numeric allocation
  with the location and connection infrastructure used by the derived index.
  Rebuildable data and ownership state have different failure semantics.
- [`census.py`](src/tangle/census.py), [`packet.py`](src/tangle/packet.py), and
  [`manifest.py`](src/tangle/manifest.py) explain that historical benchmark inputs
  constrain where production changes can go. Evidence should freeze fixtures,
  not the architecture of live source files.
- [`tests/test_skill.py`](tests/test_skill.py) protects many exact prose strings.
  Some grammar needs literal tests, but accumulated operating advice should not
  require a particular sentence forever.

The documentation also exposes complexity that is not simply implementation
size. [`SKILL.md`](SKILL.md) currently has 1,812 whitespace-delimited words and
12,278 bytes, including clock edge cases, migration milestones, and worker
ownership exceptions. [`references/coordination.md`](references/coordination.md)
even carries Rust-specific implementation advice in a general graph workflow.
Those are signs that lessons from individual sessions have become global rules.

[`NOTES.md`](NOTES.md) correctly identifies the product tension: small nodes help
agents but fragment human understanding, while orientation and bookkeeping can
consume the savings. [`ASTRA.md`](ASTRA.md) gives a useful direction, but some
observations have already aged: the current packet includes manifest paths,
verification, compatibility constraints, and completion criteria. Extend that
working surface rather than treating it as missing. The sealed proposal and
receipt system in [`references/change-intake.md`](references/change-intake.md)
also describes intended commands; it should not be counted as an already
implemented transaction engine.

## 1. One interpretation of the files

Use a concrete, modest library boundary:

```text
Markdown files
      |
      v
format + loader --> immutable Graph snapshot
                           |
                    validate + query
                           |
               execution policy + edit plans
                           |
                  CLI / packets / views

Optional search and coordination tools call these same boundaries.
The graph library never imports them.
```

Do not build a general graph database, workflow framework, or plugin kernel.
Use ordinary modules, typed records, and explicit functions. Initially the
shipping command can contain the core and its execution layer in one package;
separate responsibilities do not require separate services.

### Core data model

The in-memory model needs only a handful of concepts:

| Record | Essential content |
|---|---|
| Document | Stable identity, path, raw bytes/hash, parsed fields, body sections, source locations |
| Node | Kind, status, summary, semantic revision, primary route, next action |
| Edge | Source, target, relationship class, optional pinned revision, source location |
| Graph | Nodes, roots, outgoing edges, and derived incoming edges |
| Diagnostic | Stable code, severity, node/location, expected and actual values, repair guidance |

Normalize relationship spellings into a few behaviors: **containment**, **pinned
context**, **gate**, and **reference**. Preserve their authored labels. `Parent`
and `Area` share containment mechanics; `Depends on`, `Requires`, `Implements`,
and `Governed by` share revision mechanics. Supersession remains a reference with
explicit execution-policy rules. Free prose links remain navigational references
and do not acquire dependency semantics.

Keep arbitrary body prose intact. The parser recognizes a documented metadata
subset and reserved relationship forms outside code fences; it does not extract
machine authority from every English sentence. Parse once, retain source spans,
and share the result across checking, routing, mutation, and rendering. Report
malformed reserved syntax instead of silently losing an edge. Preserve unknown
fields when editing, but reject unsupported format versions rather than guessing
their meaning.

### Keep the current files initially

The stationary Markdown store already solves an important problem: changing
status does not change identity or break links. Preserve filenames, canonical
paths, wikilinks, and semantic revisions. Changing languages, relationships,
identities, and storage layout in one rewrite would obscure whether the new
architecture is any better.

Keep current random IDs internally. Let commands resolve unique prefixes and
titles, reject ambiguous inputs with choices, and persist full canonical targets.
This deliberately changes the current restriction on abbreviated input, without
creating a shared numeric allocator or making a mutable title authoritative.
Readable summaries should dominate displays.

Use one isolated legacy reader during a documented transition. Keep migration
an explicit command with preview and recovery; ordinary reads should not migrate
a vault. Once compatibility can end, remove the reader instead of retaining
two storage models in every operation.

## 2. A deterministic execution layer

Tangle is more useful than a bag of graph primitives. Ship one opinionated
execution layer, tested independently of the CLI, which owns:

- Containment reachability and root selection.
- Explicit `next` routes and their direct-child constraint.
- Status, gates, pinned-context readiness, and staleness.
- Completion requirements and coordinating-parent behavior.

That concentrates policy without inventing a configurable rules engine. Node
kinds can select small built-in validation functions. Feedback-specific fields
belong to the feedback layer; manifest verification commands belong to project
configuration or authored manifests. The graph engine should not hardcode this
repository's `make test` vocabulary as the only valid verification language.

Expose a narrow functional API, approximately:

```text
load(root)                         -> Graph + parse diagnostics
validate(graph)                    -> Diagnostic[]
resolve(graph, scope?)             -> Ready | Blocked | Ambiguous | Invalid
impact(graph, node)                -> affected consumers and edge paths
plan_edit(graph, operation)        -> EditPlan | Diagnostic[]
apply(edit_plan, expected_hashes)   -> Applied | Conflict
```

`resolve` follows authored routes. With multiple independent eligible routes,
it returns ambiguity; ranking cannot silently select an assignment. If a route
is gated, it reports the gate without jumping into its target as implied work.
A cleared gate permits readiness reevaluation but does not automatically create
a pin or resolve the consumer. A pinned target must be resolved at the recorded
revision. An explicit external blocker remains blocked until someone clears it.

Keep the four existing statuses for compatibility. Readiness is derived from
status, routes, gates, and pins; it is not a fifth stored flag. `active` is never
ownership. An error affecting the selected route or its required context prevents
a ready result. Unrelated errors remain visible diagnostics; the global checker
still reports all of them. This scoped-error policy is a proposed contract choice
to test explicitly against current behavior.

Avoid several implementations of “next.” `packet`, candidate listings, human
views, and any future API consume the same resolution result, including its
route evidence. Semantic suggestions cannot override it.

## 3. Make mutation small and honest

Direct Markdown editing stays supported. Authoring helpers should perform the
repetitive work through a few explicit operations: create, record progress,
resolve, and revise context. They should produce a reviewable patch using the
same model and validator as read operations.

For helper-driven changes:

1. Load the starting bytes and compute an edit plan.
2. Require an explicit semantic-change choice when context changes. Stamp
   `updated` from the host clock; preserve the current monotonic clamp rule.
3. Validate the prospective graph and show actionable errors.
4. Check expected hashes under a short writer lock before applying changes.
5. Replace individual files through same-directory temporary files and rename.

A hash check alone is not compare-and-swap on ordinary files: the lock serializes
cooperating writers. It cannot protect against an editor that ignores that lock.
The base operating assumption is one writer per checkout; stronger isolation
belongs to the coordination layer.

Nor does atomic rename make a multi-file update atomic. For a child resolution
and parent advance, validate one combined patch, apply under exclusive ownership,
and commit both coherently. A crash between writes leaves a checkable intermediate
state; retain the proposed patch so the user can finish or revert it. If actual
transactional publication is required, use a candidate Git tree and integration
through the optional Git adapter. Do not quietly implement a second transaction
log in the core.

Hashes and semantic revisions have distinct purposes. The hash detects changed
bytes; `context_rev` means consumers must reconsider an assumption. A helper
cannot infer that meaning reliably, and a fresh agent has not read a dependency
merely because its pin matches. Never auto-refresh stale pins to make checks pass.

## 4. Useful layers above the resolver

### Agent interface: one packet and a short loop

Make `tangle packet [scope]` sufficient to begin bounded work. Include the task's
next action, acceptance criteria, selected route, blockers, required context,
source/test paths, and verification instructions. Include content hashes for the
material used to assemble it. Present verification instructions as data; printing
a packet must not execute commands embedded in Markdown.

Reuse the current manifest and packet implementation's working behavior. Improve
context assembly: include essential dependency content or an explicit list of
required reads, and clearly name omissions when a size bound is reached. Do not
hide necessary context behind an attractive token count. References can be
optional reads; pinned context cannot silently be treated the same way.

The skill can then be roughly 300–500 words: when to retain memory, request a
packet, read its requirements, perform the authorized slice, record evidence, and
check graph changes. Admission, semantic changes, and completion still require
judgment. Commands own format details, timestamps, diagnostics, and links to
conditional help. Task-specific language and compilation guidance belongs in
the task's manifest or the host repository's instructions.

### Human interface: composed documents

Generate an initiative document from authored intent and the graph: purpose,
approach, decisions, completed outcomes, open tasks, and the next action. Link
each section to its authoritative node. Keep generated pages disposable and
human-authored narrative in a single canonical place.

VISION → PLAN → tasks can start as presentation conventions over containment.
It need not introduce another lifecycle or require turning every paragraph into
a node. Solve fragmentation by composition before changing node boundaries.

### Search and planning assistance

Ship plain text search first. Optional lexical indexing, embeddings, clustering,
duplicate suggestions, and proposed decompositions consume graph exports. Their
outputs are recommendations with source links, not accepted graph transitions.
An unavailable model must not affect validation or execution readiness.

Use a versioned JSON export and ordinary CLI/subprocess calls for out-of-process
consumers. In-process views can call the library. This is enough of an extension
boundary; dynamic plugin discovery and a universal event bus would add machinery
before there are requirements for it.

### Coordination: choose a supported operating mode

Default to one writer per checkout and no work-session claims. For parallel
workers, prefer isolated Git worktrees and one integrator. An assignment contains
a base commit, packet/context hashes, and declared scope; workers return code and
graph changes together. Integration rechecks the merged graph and repository
tests even after a clean textual merge.

Shared-checkout concurrency needs an optional coordinator that owns overlapping
source-file write sets, not just node leases. Put its live state in a separate
store from caches. Losing that state requires establishing ownership again;
rebuilding a graph index cannot prove that old workers stopped.

For asynchronous or multi-host contributions, begin with branches or patches
and explicit integration. Defer the proposed sealed-object, acceptance-record,
and receipt protocol until ordinary Git exchange demonstrably lacks a required
capability. If that protocol is needed, it should be a separate product layer
calling validation and edit planning, with its own recovery tests.

## 5. Start without persistent index maintenance

The current stationary store contains 271 Markdown nodes. That is a reason to
measure a direct scan before designing incremental machinery, not proof that
scans meet a latency target.

Initially, read the vault into memory once per command, parse each file once,
derive adjacency maps, and answer every query from that graph. Discovery/parsing
is linear in input bytes; ordinary reachability and dependency traversals are
linear in nodes plus edges. Read commands neither regenerate views nor require
creating state under the user's home directory. Generate views on explicit
request; watchers can be an optional convenience later.

For a single writer this yields a simple consistency contract. A filesystem scan
is not a transaction across concurrent edits. Coordinated readers/writers use
the checkout lock, or queries use an immutable Git tree. Detectable interference
should return a retryable error, without claiming that hashing alone establishes
a globally consistent snapshot.

If measurement later justifies caching, cache parsed documents by exact content
hash. Hash current canonical bytes before using cached parses for authoritative
answers; preserved mtimes must not hide edits. This still reads the files and
only saves parsing. A search index may accelerate candidate discovery, but
readiness and final results must be checked against current documents. Keep
caches scoped to the vault/worktree, since sibling worktrees can differ.

SQLite is a reasonable optional search backend. It should be replaceable by
deleting a cache directory, without affecting leases or durable data. There is
no need for an always-running service in the initial architecture.

## 6. A concrete implementation boundary

```text
src/tangle/
  model.py        # records and diagnostics
  format.py       # one parser, source spans, targeted rendering
  graph.py        # loading, identity resolution, edges, traversals
  execution.py    # validation, readiness, routes, impact
  edits.py        # prospective changes and guarded file application
  packet.py       # agent context composition
  views.py        # human document composition
  cli.py          # argument parsing and text/JSON rendering

extras/
  search/         # optional index and model runtime
  coordination/   # assignments, Git integration, optional live claims
  migration/      # bounded compatibility tools

research/         # evaluation runners and frozen historical source fixtures
```

Treat **3–5 KLOC for the core, execution policy, and file editing**, and another
**1–2 KLOC for the ordinary CLI and views**, as review budgets, not estimates
backed by an implementation. Tests, vendor libraries, research, and genuinely
optional extensions are outside those numbers. If essential behavior cannot fit,
reassess the contract before golfing code or hiding it behind abstractions.

A prepared installation should expose exactly one executable and one selected
skill location per agent scope. Package management happens during installation
or upgrade. A missing runtime gives a repair instruction instead of attempting
dependency resolution on the first graph query. This addresses the cache friction
in `NOTES.md` without requiring a language migration.

## 7. Replace in slices, with explicit deletions

1. **Separate evidence from the runtime.** Move research dispatch out of ordinary
   startup and snapshot historical prompt source under research fixtures.
   Preserve the measurements and their provenance. This makes later refactoring
   independent of benchmark source-layout constraints.
2. **Introduce the shared graph model.** Read the current vault and adversarial
   fixtures with one parser. Compare identities, edges, diagnostics, routes,
   gates, and pin states with current behavior. Preserve supported behavior;
   document deliberate differences instead of treating every old result as right.
3. **Replace the daily read path.** Put `check`, `packet`, node inspection, and
   impact on the shared snapshot. Demonstrate that they work with no sidecar,
   no model installation, and an unwritable package cache. Remove superseded
   parsers and duplicate route implementations as each consumer moves.
4. **Consolidate authoring and instructions.** Add guarded edit helpers, reduce
   the skill, and replace prose-preservation tests with behavioral scenarios
   where appropriate. Coordinate changes to current contracts for mandatory
   claims, automatic upkeep, abbreviated inputs, and scoped diagnostics; these
   are intentional policy changes, not transparent refactors.
5. **Add composed views; opt into concurrency or search only when needed.**
   Remove the old runtime's orphaned command paths. Retire compatibility on its
   announced schedule. Do not make feature parity with every experimental verb
   a condition of shipping the simpler product.

Use a small set of acceptance scenarios: a cold worker receives the intended
action; two initiatives remain ambiguous; a changed decision invalidates its
consumer; a cleared gate does not complete work; a partial result resumes; a
parent cannot resolve prematurely; a direct edit is visible despite unchanged
mtime; a conflicting helper write is rejected; combined code/graph integration
revalidates assumptions. Test crashes where writes actually occur, and retain
parser fixtures for malformed metadata and links.

Most tests should call pure functions over tiny in-memory graphs. Keep a bounded
CLI/installer integration suite and separate research verification. Measure
startup and packet latency at actual and synthetic vault sizes, required follow-up
reads, output size, and suite duration. These are inexpensive indicators, not
proof of lower model token use or better autonomous execution.

## The simplifying decision

Tangle should own **the interpretation of execution memory**. Let Git own history
and branch integration, editors own prose, renderers own human composition,
optional models suggest organization, and coordinators own worker scheduling.

The decisive reduction comes from one parser, one resolver, one editing path,
and fewer mandatory operating rules. A rewrite that reproduces every existing
exception, experimental command, and future intake protocol would recreate the
same system in a different language.
