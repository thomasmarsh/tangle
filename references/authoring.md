# Authoring reference

Load this before writing node bodies, recording feedback, capturing a node with
one command, decomposing or rolling up work, or editing `index-map.md`. It is the
canonical Markdown source that `braintree help authoring` prints, and it is
installed beside `SKILL.md` at the same revision as the `braintree` command.

## Node body and status output

Use body headings only for additional information: `# Context` (with
`Depends on [[...]] at context_rev N.`), `# Blocked` (`Blocked by`/`Unblocks
when`), `# Outcome`, `# Done when`, `# Result`, `# Invariant` for definitions,
and `# Feedback` for feedback nodes. A `DEC` node records a settled choice under
`# Decision`/`# Rationale`/`# Consequences`. A settled `DEF` or `DEC` is
`resolved`; while its invariant or decision is still unsettled it stays
`proposed`, so resolving it is the act of settling it. A resolved `DEF` or `DEC`
is current knowledge unless its sparse `disposition` says `deprecated` or
`superseded`. Index nodes contain pointers, not copied content.

Report graph lists in compact TOON, not JSON or narrative tables, with only the
fields needed, e.g.
`nodes{id,status,priority,context_rev}: TAS-101,active,P1,3 | DEF-auth,resolved,,7`.
State zero results explicitly, and name the resolved node, new status, and
advanced frontier in a completion report.

## Index contract

`.braintree/index-map.md` holds intent and routing, not state: a short `# Focus` list,
durable area entry pointers, and tested query recipes. Never copy node status,
priority, revision, timestamp, or summary into it. A focus pointer is advisory;
validate its target before acting.

## Decomposition and roll-up

Decompose just in time, only after the node-admission threshold, at a distinct
independently resumable outcome, blocker, dependency, or verification boundary
that also retains durable execution-memory value. A child states its outcome or
decision, completion criterion, primary `Parent`/`Area` route, and executable
`next`. Do not pre-create speculative trees. A user-requested plan is not
speculative decomposition: create its children up front as `proposed` work and
resolve or dispose each as reality arrives.

A direct child is a node whose primary `Parent` or `Area` is the current node. A
coordinating task states its outcome and `Done when` criteria; its `next` is
either one concrete frontier action or one wikilinked direct child at the current
frontier, never a child list. Roll up from evidence, not child counts.

## Direct answers

```sh
braintree frontier  # frontier
braintree node ID  # one node
braintree impact ID  # dependency impact
braintree orient  # orientation packet
braintree digest ID  # unresolved direct members of a hub or node
braintree clusters  # advisory clusters, over-broad routes, and outliers
find .braintree -type f -name 'TAS-*.md' | rg '/(active|proposed|blocked)/'          # unfinished
find .braintree -type f -path '*/active/TAS-*.md' -exec rg -l '^priority: P0$' {} +  # actionable P0
rg -n '^(Parent|Area) \[\[' .braintree                                               # primary routes
```

`braintree digest ID` bounds the summaries and `next` of one hub's or
coordinating node's unresolved direct members. `braintree clusters` returns
advisory cluster groupings, over-broad routes, noise, and outliers, and only when
the optional semantic capability is installed; without it, it prints one advisory
line and exits zero. Neither answer is a claim, assignment, or authority. Prefer
bounded results, and do not repeat a backlink search through returned dependents;
`braintree impact ID` traverses the chain directly.

## Capturing a node

`braintree node record` creates one routed, correctly-stamped node of a named
type from a summary and body, the way `braintree feedback record` does for `FBK`:

```sh
braintree node record --type THO \
  --summary 'Does a claim survive a worktree move?' \
  --body 'Question: does a claim survive a move between worktrees?'
```

- `--type` is one of `THO`, `DEF`, `DEC`, or `TAS`. `FBK` friction is recorded
  with `braintree feedback record`, and a root `IDX` hub is declared in
  `index-map.md`, so neither is a capture target.
- The command allocates the next id from Markdown, discovers the primary route to
  the vault's root hub from `index-map.md`, and stamps a positive `context_rev`
  and the current `updated`, so the result is a routed node the checker accepts.
- It reserves that id atomically before writing the file, and both one-command
  capture paths share this one allocation contract. When the project's sidecar
  exists and the target `.braintree/` directory is inside the project's own worktree,
  the reservation comes from the same atomic counter `braintree allocate PREFIX`
  uses, so parallel worktrees cannot choose the same number. Otherwise it
  reserves a vault-local marker under `.braintree/reservations/` with an exclusive
  create, which is collision-safe for callers sharing that vault but does not
  span worktrees; preallocate with `braintree allocate PREFIX` and pass `--id`
  when parallel creation crosses worktrees without an initialized sidecar.
- `--status` names the status directory and defaults to `proposed`; the caller
  owns the body the type and status need, so a `blocked` body carries a
  `# Blocked` section with `Blocked by` and `Unblocks when`.
- A `TAS` node in an unfinished status requires `--next` carrying its one action,
  and a `resolved` node must omit `--next`, matching the `next` rule the checker
  enforces.
- `--route 'Area [[IDX-...]]'` overrides the discovered route, `--id` and
  `--slug` override the allocated id and the derived slug, `--summary` overrides
  the derived summary, and `--nodes` selects a vault directory other than the
  current one.

The admission threshold is unchanged: the command creates the node the caller has
already decided to admit, and it never admits a note with no foreseeable decision
or action value on its own.

## Feedback nodes

A consuming project records Braintree friction as an `FBK` node. The `FBK` type
is the one feedback marker, so `find .braintree -name 'FBK-*.md'` discovers feedback
from Markdown alone, with no sidecar, network, or write to the scanned vault.

- Name it `FBK-<n>-<slug>.md` and give it one primary `Parent` or `Area` route
  into its own vault, like any node.
- Carry the installed Braintree revision as `braintree_revision:` frontmatter,
  for example `braintree_revision: 0.6.0+g1b58d57`; write
  `braintree_revision: unknown` when no revision can be determined.
- Read the revision to record with `braintree --version`: an installed skill
  prints the installer's generated `installed-revision` stamp,
  `<version>+g<short-sha>`, or `<version>+unknown` when the source revision could
  not be determined. Treat the public `<version>` as the compatibility signal and
  the `+g<short-sha>` as provenance: decide compatibility from the version, and
  never resolve the source revision against the remote, which the offline record
  cannot support.
- State the friction in one `# Feedback` section with an `Attempted:`, a
  `Friction:`, and an `Improvement:` line.

`braintree check` rejects an `FBK` node that omits or malforms
`braintree_revision` or lacks the required `# Feedback` content.

Record feedback with the writing half of the mechanism. Run
`braintree feedback record` from the consuming project's vault root and it
allocates the next `FBK` id from Markdown, routes the node to the vault's root
hub, stamps the revision from the installed record, and writes
`.braintree/proposed/FBK-<n>-<slug>.md` in one step. The id is reserved atomically by
the same capture contract as `braintree node record`.

```sh
braintree feedback record \
  --attempted '...' --friction '...' --improvement '...'
```

`--nodes` points at the vault's `.braintree/` directory when it is not the
current directory. `--route 'Area [[IDX-...]]'` overrides the route discovered from
`index-map.md`. `--id`, `--summary`, and `--slug` override the allocated id, the
summary derived from the friction, and the derived slug. The command reads the
installed `installed-revision` record and degrades explicitly to
`<version>+unknown` when no record is present, so the node always names the
Braintree version in use. The result is a valid, routed `FBK` node that
`braintree check` accepts.

To collect feedback from another vault, run the read-only
`braintree feedback scan` command over one or more vault roots:

```sh
braintree feedback scan /path/to/vault
```

It reads only `FBK-*.md` frontmatter and prints compact TOON with each node's
vault, id, status, Braintree revision, and summary; it prints
`feedback: 0 nodes` when there is none. It works on a read-only checkout with no
sidecar or network, and never writes to the scanned vault.

Triage each scanned result into this graph: admit a node only when the friction
is likely to change a future decision or action, cite the feedback id and
revision in the admitted node, and otherwise dispose the result explicitly rather
than dropping it silently.
