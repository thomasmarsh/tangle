# Authoring reference

Load this before writing node bodies, recording feedback, capturing a node,
decomposing or rolling up work, proving a negative assertion, or editing
`index-map.md`. It is the canonical Markdown printed by
`tangle help authoring` and is installed with `SKILL.md` and the command.

## Bodies, knowledge nodes, and reports

Use body headings only when they add information:

- `# Context`, including `Depends on [[...]] at context_rev N.`
- `# Blocked`, with `Blocked by` and `Unblocks when`
- `# Outcome`, `# Done when`, and `# Result`
- `# Invariant` for definitions and `# Feedback` for feedback nodes
- `# Decision`, `# Rationale`, and `# Consequences` for decisions

A settled `DEF` or `DEC` is `resolved`; keep it `proposed` while its invariant
or decision is unsettled. A `DEF` resolves only when every consumer-visible
shape its consumers must author is defined in it, or the definition explicitly
names the successor node that will define it; a shape deferred to an
implementing task with no named successor is disallowed at resolution. An
additive consumer-visible shape names the definition version, or the other
signal a consumer reads, that distinguishes a consumer with the new shape from
one without, because an unversioned additive slice leaves a consumer unable to
tell the two apart. Resolved knowledge remains current unless its sparse
`disposition` says `deprecated` or `superseded`.

Report graph lists in compact TOON, not JSON or narrative tables, with only the
needed fields, for example
`nodes{id,status,priority,context_rev}: TAS-101,active,P1,3 | DEF-auth,resolved,,7`.
State zero results explicitly. A completion report names the resolved node, its
new status, and the advanced frontier.

## Index contract

`.tangle/index-map.md` holds intent and routing, not state: keep only a short
`# Focus` list, durable `Indexes [[IDX-...]]` pointers, and tested query recipes.
Never copy node status, priority, revision, timestamp, summary, or hub members
into it. A focus pointer is advisory; validate its target before acting.

## Decomposition and roll-up

Decompose just in time, only after the node-admission threshold, at a distinct
independently resumable outcome, blocker, dependency, or verification boundary
that also retains durable execution-memory value. That boundary evidence is
semantic, not predictive, so it can arrive before dispatch: when the authored
`# Done when` already names several outcomes that each carry their own
acceptance, verification, consumption, blocking, resumption, or rollback
boundary, the coordinator may create one direct child per outcome before
dispatch and keep the original node as their coordinating parent. The parent's
`# Done when` remains the coordinator's acceptance and its `next` routes to the
first child; duration, worker windows, token or model budgets, file counts, and
anticipated commits are never evidence, and several implementation steps that
together produce one acceptance outcome remain one node, executed as slices.
A child states its outcome or decision, completion criterion, primary `Parent
[[...]]` or `Area [[IDX-...]]` route, and executable `next`. Do not pre-create
speculative trees, and never manufacture children to fit a session. A
user-requested plan is also created up front: create its children as
`proposed`, then resolve or dispose each as reality arrives.

A direct child uses the current node as its primary route. A coordinating task
states its outcome and `# Done when`; its `next` is one concrete frontier action
or one wikilinked direct child, never a child list. Roll up from evidence, not
child counts.

When the decomposition is deliberate, author it in one transactional step
instead of one capture per child. `tangle node decompose --parent PARENT
--plan FILE` validates the whole plan before it mutates anything, generates each
child's id, writes each child with the canonical `Parent [[PARENT]]` route and
its executable `next`, and advances the parent's `next` to the first child. The
plan is one JSON document:

```json
{"children": [
  {"type": "TAS", "summary": "Validate signed manifests.",
   "next": "Run the signed-manifest validation.",
   "body": "# Context\n\n..."}
]}
```

`type` is a capture type, `summary` and `body` are required, `next` is required
for an unfinished `TAS`, and `status` (default `proposed`) and `slug` are
optional; an unknown key is rejected rather than ignored. `--dry-run` validates
and prints the ordered plan without writing. A rejected plan writes nothing; a
write failure removes the children already written and leaves the parent
unchanged. The command never writes a reciprocal child list, never rewrites the
parent's `# Done when` or body, and never infers a semantic boundary the plan did
not declare: it only routes and stamps. `tangle node advance PARENT CHILD` is
the parent-advance-only shorthand for a case where only that one line needs to
change; prefer it over hand-editing the parent when no other edit is due.

An increment brief — a node's body or a worker handoff — that places a new
artifact in an existing directory carries a "gates my artifact enters" line
naming the test suites that enumerate that directory, before the artifact path
is chosen; a gate that walks a directory and asserts a property of every file
in it can reject a correctly authored new file, so the enumerating suite is a
path constraint rather than a verification surprise.

When a shared-stage change assumes new state or capability across heterogeneous
participants, the increment brief names a falsifying mixed-capability acceptance
input: one participant carries the new state or capability and an existing
participant in the same stage does not. The brief also names that case's expected
fallback or rejection behavior, so a non-panic alone is not acceptance.

## Opt-in reconnaissance references

A node records that durable reconnaissance informed it with a non-pinned
`Informed by [[TARGET]].` line in `# Context`, where `TARGET` is a knowledge node
(`THO`, `DEF`, or `DEC`). The relation is one-directional and stored only on the
consumer; a node may cite several targets, one line each, and must not repeat a
target. It is deliberately not a dependency: it carries no `context_rev` pin, so
it never affects readiness, staleness, primary routing, ownership, or automatic
context loading, and `tangle node` never follows it.

Use it for shared orientation that a reader may want but that must not become a
blocking edge — reconnaissance a `THO` already owns instead of restating it in
every task. `tangle node references NODE` is the opt-in read surface: it
returns the node and its directly referenced reconnaissance in one deterministic
hop, so a reference cycle between two nodes terminates, and it reports a target
that is absent as `missing` rather than dropping or failing. `tangle check`
validates only the relation's structure — the exact line form, its `# Context`
placement, a knowledge-node target, no duplicate target, and the existing
broken-link rule — and never judges whether the referenced context is useful.

## Negative assertions

Prove the absence of a branch on a named mode or scenario with an observable
check when possible. Otherwise, a checked-in source-text guard over the module
is an acceptable negative assertion when it is paired with a falsification
probe: a fixture source that carries the forbidden token and that the guard must
reject, so the test fails when the guard stops detecting rather than when the
forbidden token merely moves. The guard names the exact tokens it forbids and
the modules it covers, and matches whole tokens rather than substrings.

## Capturing a node

After deciding that a node meets the admission threshold, capture it in one
step; the command does not decide admission:

```sh
tangle node record --type THO \
  --summary 'Does a claim survive a worktree move?' \
  --body 'Question: does a claim survive a move between worktrees?'
```

`tangle node record` accepts `THO`, `DEF`, `DEC`, or `TAS`; use
`tangle feedback record` for `FBK`, and declare root `IDX` hubs in
`index-map.md`. It generates a lowercase 128-bit id from cryptographic entropy,
writes one stationary file under `canonical/<suffix>/`, discovers a route to the
root hub, and stamps `context_rev` and `updated`. Because ids come from entropy,
parallel writers never collide and need no shared sequence or preallocation.
`--id` accepts only a canonical lowercase identity for a caller that must
reproduce one; `tangle allocate` and `tangle reservations` remain only for
a legacy numeric prefix during the compatibility window.

The caller supplies body fields required by the selected type and status. An
unfinished `TAS` requires one `--next`; a resolved node omits it; a blocked node
has `# Blocked`, `Blocked by`, and `Unblocks when`. See
`tangle node record --help` for overrides.

`--summary` is one line of at most 96 characters. A longer value is shortened
at the last word boundary that leaves room for a trailing `...`, and the command
prints a `warning:` line naming the limit, so a capture never stores a mid-phrase
summary.

The derived filename slug is the summary lowercased and hyphenated, capped at 48
characters and cut at the last whole-word boundary inside the cap; a single word
longer than the cap is clipped at it. Pass `--slug` to override the derived slug
entirely, which is the escape hatch when even a whole-word cut is not the
basename you want to reproduce in wikilinks. As with `--summary`, an explicit
`--slug` is taken as given and is not word-boundary processed.

## Feedback nodes

A consuming project records Tangle friction as an `FBK`/`fbk` node. The
feedback type is the one feedback marker, so
`find .tangle -iname 'fbk-*.md'` discovers feedback from Markdown alone, with
no network access and no write to the scanned vault.

One session records one session `FBK` node, and the coordinator owns it: a
worker that hits friction reports it in its run report — the attempted action,
the friction, and the improvement — instead of creating a node, and the coordinator
decides whether that report becomes the session `FBK` node, folds into one
already recorded, or is disposed. A worker creates an `FBK` node only when the
coordinator explicitly grants it. The one-per-session rule scopes to the
orchestration session, not to each worker run, so two workers that each hit
friction in one session owe one report, not two nodes.

Each feedback node:

- has one primary `Parent [[...]]` or `Area [[IDX-...]]` route;
- carries `tangle_revision:` from `tangle --version`, using
  `<version>+g<short-sha>`, `<version>+unknown`, or `unknown` when unavailable;
- has one `# Feedback` section with an `Attempted:`, a `Friction:`, and an
  `Improvement:` line.

The public version is the compatibility signal and the short SHA is provenance;
never resolve that SHA against a remote. `tangle check` rejects malformed
feedback metadata or content.

From the consuming vault root, `tangle feedback record --attempted '...'
--friction '...' --improvement '...'` allocates, routes, stamps, and writes a
valid proposed node through the same atomic capture contract. The derived
summary obeys the same 96-character limit and warning behavior. See its
`--help` for routing and naming overrides.

Collect feedback read-only with `tangle feedback scan /path/to/vault`. It
reads only the feedback nodes' frontmatter (canonical `fbk-*` and legacy
`FBK-*`), prints compact TOON fields for each result, prints `feedback: 0 nodes`
for none, and works without local state or network in a read-only checkout. Triage each result into this graph: admit it only when it
is likely to change a future decision or action, cite its ID and revision, and
explicitly dispose the rest.
