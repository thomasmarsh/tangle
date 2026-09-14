# Authoring reference

Load this before writing node bodies, recording feedback, capturing a node,
decomposing or rolling up work, proving a negative assertion, or editing
`index-map.md`. It is the canonical Markdown printed by
`braintree help authoring` and is installed with `SKILL.md` and the command.

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

`.braintree/index-map.md` holds intent and routing, not state: keep only a short
`# Focus` list, durable `Indexes [[IDX-...]]` pointers, and tested query recipes.
Never copy node status, priority, revision, timestamp, summary, or hub members
into it. A focus pointer is advisory; validate its target before acting.

## Decomposition and roll-up

Decompose just in time, only after the node-admission threshold, at a distinct
independently resumable outcome, blocker, dependency, or verification boundary
that also retains durable execution-memory value. A child states its outcome or
decision, completion criterion, primary `Parent [[...]]` or `Area [[IDX-...]]`
route, and executable `next`. Do not pre-create speculative trees. A
user-requested plan is the exception: create its children up front as
`proposed`, then resolve or dispose each as reality arrives.

A direct child uses the current node as its primary route. A coordinating task
states its outcome and `# Done when`; its `next` is one concrete frontier action
or one wikilinked direct child, never a child list. Roll up from evidence, not
child counts.

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
braintree node record --type THO \
  --summary 'Does a claim survive a worktree move?' \
  --body 'Question: does a claim survive a move between worktrees?'
```

`braintree node record` accepts `THO`, `DEF`, `DEC`, or `TAS`; use
`braintree feedback record` for `FBK`, and declare root `IDX` hubs in
`index-map.md`. It allocates the next id from Markdown, discovers a route to the
root hub, stamps `context_rev` and `updated`, and reserves the ID before writing.

When project-local coordination exists and the target vault is in the project
worktree, capture shares the atomic counter used by `braintree allocate`.
Otherwise it uses an exclusive vault-local marker: safe for callers sharing the
vault, but not across worktrees. Before coordination state exists, parallel
worktrees must preallocate with `braintree allocate PREFIX` and pass `--id`.

The caller supplies body fields required by the selected type and status. An
unfinished `TAS` requires one `--next`; a resolved node omits it; a blocked node
has `# Blocked`, `Blocked by`, and `Unblocks when`. See
`braintree node record --help` for overrides.

`--summary` is one line of at most 96 characters. A longer value is shortened
at the last word boundary that leaves room for a trailing `...`, and the command
prints a `warning:` line naming the limit, so a capture never stores a mid-phrase
summary.

## Feedback nodes

A consuming project records Braintree friction as an `FBK` node. The `FBK` type
is the one feedback marker, so `find .braintree -name 'FBK-*.md'` discovers
feedback from Markdown alone, with no network access and no write to the scanned
vault.

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
- carries `braintree_revision:` from `braintree --version`, using
  `<version>+g<short-sha>`, `<version>+unknown`, or `unknown` when unavailable;
- has one `# Feedback` section with an `Attempted:`, a `Friction:`, and an
  `Improvement:` line.

The public version is the compatibility signal and the short SHA is provenance;
never resolve that SHA against a remote. `braintree check` rejects malformed
feedback metadata or content.

From the consuming vault root, `braintree feedback record --attempted '...'
--friction '...' --improvement '...'` allocates, routes, stamps, and writes a
valid proposed node through the same atomic capture contract. The derived
summary obeys the same 96-character limit and warning behavior. See its
`--help` for routing and naming overrides.

Collect feedback read-only with `braintree feedback scan /path/to/vault`. It
reads only `FBK-*.md` frontmatter, prints compact TOON fields for each result,
prints `feedback: 0 nodes` for none, and works without local state or network in
a read-only checkout. Triage each result into this graph: admit it only when it
is likely to change a future decision or action, cite its ID and revision, and
explicitly dispose the rest.
