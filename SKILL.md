---
name: knowledge-execution-graph
description: Manage engineering work in a local Markdown vault as atomic, wikilink-connected nodes with authoritative status directories and dependency-revision checks. Use when the user invokes this skill or asks to plan, track, or execute work through a Markdown knowledge graph; do not use for ordinary Markdown editing.
---

# Knowledge Execution Graph

Use the vault as a low-overhead execution graph. Keep planning, decisions, definitions, component notes, bug traces, and task state durable without loading unrelated context.

## Vault contract

- Treat the directory containing `nodes/index-map.md` as the vault root.
- Store each node under exactly one authoritative status directory: `nodes/proposed/`, `nodes/active/`, `nodes/blocked/`, or `nodes/resolved/`. Create these directories only as needed.
- Keep each node about one task, thought thread, component definition, file index, or bug trace. Split a file when topics become independently actionable.
- Name nodes `<ID>-<short-slug>.md`, preserving the vault's existing ID convention. Prefixes such as `TAS`, `THO`, `DEF`, and `IDX` express type; represent bug work with `BUG` only when the vault already uses it, otherwise use a task ID.
- Connect nodes with Markdown wikilinks. Prefix every link with its relationship, for example `Depends on`, `Implements`, `Parent`, or `Indexes`.
- Store each relationship in one canonical direction: put `Parent` on the child, `Area` on the node assigned to that area, `Depends on` (and other pinned context dependencies) on the consumer, `Superseded by` on the obsolete node, and `Indexes` on `index-map.md` or another deliberate route. Derive `Child`, `Parent of`, `Indexed by`, backlinks, and depended-on-by views with exact searches; do not store them as reciprocal edges.
- A parent may point to a child only through a distinct, deliberate route such as its `next` frontier. That route is not a copied `Child` relationship or a catalog.
- Keep prose terse. Store conclusions and executable state, not transcripts or expansive reasoning.

The filename is authoritative for ID and type; the containing directory is authoritative for status. Do not duplicate those values in frontmatter.

## Node admission

Admit a node only when its concise conclusion or executable state is likely to
change a future decision or action. This includes durable knowledge, architectural
or operational decisions, executable tasks, bugs, technical debt, blockers, and
future features when each changes what someone should do later.

Do not admit conversation transcripts, tool-call logs, routine narration or
status, duplicate source material, or observations with no foreseeable decision
or action value. Keep a source link or a short evidence conclusion when needed;
do not copy the source into the graph.

Prefer updating the existing node when new information advances the same
outcome, question, component, decision, or defect. Independent resumability is
necessary but not sufficient for a distinct node: it must also retain durable
execution-memory value, likely to change a later decision or action or
materially reduce future resumption cost. Agent boundaries, exclusive write-set
boundaries, failed checks, incidental or mechanical cleanup, routine
verification, and handoffs alone never qualify; keep them in the current node's
`next`, result, evidence, or handoff. A fresh worker may continue the same graph
node; agents and nodes are not one-to-one. This is a low-friction judgment, not
a capture checklist: when no distinct future action exists, leave it out.

Every node begins with compact frontmatter:

```yaml
---
context_rev: 3
priority: P1
updated: 2026-09-10T01:30:00Z
summary: Reject expired authentication grants.
next: Add the failing boundary test.
---
```

- `context_rev`, `updated`, and `summary` are required. Start `context_rev` at `1`. It is a consumer-context revision, not an edit counter: increment it only when a change could alter an assumption, decision, invariant, interface, or other context a pinned consumer must reread. Use the current UTC ISO-8601 time for `updated` on every mutation.
- Do not increment `context_rev` for cosmetic edits, evidence or history additions, status moves, priority or `next` changes, or other local workflow changes that leave consumer-relevant context intact. Git records those edits. When uncertain, treat a change as semantic if a reasonable consumer that had reconciled the earlier node should reread it.
- `priority` is optional and normally task-only. Use `P0`, `P1`, `P2`, or `P3`; absence means unranked.
- `next` is required for proposed and active tasks. For a blocked task, use it for the concrete unblock action when one exists; otherwise omit it. Always omit it from resolved nodes.
- `disposition` is optional. Add it only when the value is `abandoned`, `deprecated`, or `superseded`; do not store `current` or empty lifecycle fields.
- Put a replacement link such as `Superseded by [[TAS-102-new-path]]` in the body rather than duplicating it in frontmatter.
- Do not add created timestamps, owners, labels, dependency arrays, or other fields unless a demonstrated local workflow earns their ongoing cost.

The status directory records the lifecycle of work on a node, not whether its knowledge remains valid. A resolved `DEF` or `DEC` is current knowledge unless its sparse `disposition` says `deprecated` or `superseded`.

## Index contract

`nodes/index-map.md` is a small intent and routing document, not a node catalog or revision ledger. It may contain:

- a short `# Focus` list of deliberate entry pointers;
- durable area or component entry pointers; and
- tested, trivial query recipes.

Never copy every node's status, priority, timestamp, revision, or summary into the index. Node mutations do not update the index. Update it only when project intent, navigation, or a query contract changes. A focus pointer is advisory: validate its target's status and header before acting.

## Parallel worktree contract

`# Focus`, `priority`, and `active` status are advisory navigation, never a work claim. For parallel work, a coordinator assigns each worker a direct node path and an exclusive write set before work begins.

- One agent writes a node and its status path at a time. Do not independently select or mutate an advisory target already assigned to another worker.
- Shared parents, `index-map.md`, definitions, and root hubs are coordinator-owned unless their writes are explicitly serialized.
- A worktree is a snapshot, not global truth. Workers do not infer that unseen work or available IDs remain unclaimed.
- The coordinator integrates child evidence, reconciles any upstream change, and alone resolves a coordinating parent after all required child work is integrated.

### Parallel ID allocation

For parallel creation, the coordinator preallocates each node ID, or assigns each worker an explicitly disjoint numeric range. A local `find` checks for an existing collision only; it is never an ID reservation. Autonomous allocation is safe only through an atomically shared reservation mechanism visible across worktrees. Branch-local `owner` or claim metadata is insufficient because separate worktrees can make the same claim without seeing each other.

### Worker handoff and serial integration

Before editing, a worker records the integration base and its assigned node path and write set. A worktree slice is not a node boundary: a fresh worker may continue the assigned node. Keep the assigned node's content update and its status move coherent in one commit or handoff bundle. Before handoff, verify every changed, created, and moved path remains in that assigned write set. Report the base, touched paths, created paths, moved paths, dependency evidence, and test evidence to the coordinator.

The coordinator integrates worker branches one at a time. Never blindly auto-merge an upstream change to the assigned node or divergent status paths: reject that handoff or perform manual semantic reconciliation before integration. After each integration, run `ruby scripts/graph-check.rb nodes`, use exact `rg -n -F 'Depends on [[ID]] at context_rev '` searches for every context-bearing dependency changed by that handoff, and reconcile stale consumers before their dependent execution. Resolve a coordinating parent only after its required child evidence has been integrated.

## Reachability contract

`index-map.md` routes to a small set of durable `IDX` root hubs with `Indexes` links. A root hub has no `Parent` or `Area` link and describes an area without listing its members. Every other node has exactly one primary, unpinned `Parent` or `Area` link. Following those primary links must terminate at a root hub; an unfinished node may also be entered directly through a deliberate `# Focus` pointer.

Treat an unfinished node that cannot reach a root hub or deliberate focus route as an orphan and a graph-integrity failure. Derive each hub's members with an exact `Parent`/`Area` backlink search; never copy them into a hub or the index. Add a hub only when a durable project or area entry needs one, then route to it from the index.

When bootstrapping an empty vault, create `nodes/index-map.md`, a resolved/current `IDX` root hub with no `Parent` or `Area`, and an `Indexes` route from the index to that hub. Then create the needed status directory and the first actionable node at `context_rev: 1`, giving it exactly one `Area` route to the hub (or a `Parent` route when it is a child). Do not create broad catch-all planning files.

## Decomposition and roll-up

Decompose just in time only after the node-admission threshold is met: current
execution needs a distinct independently resumable outcome, blocker, dependency,
or verification boundary that also retains durable execution-memory value. A
child must say enough to resume without reopening its parent: its own concise
outcome or decision, completion criterion, primary `Parent`/`Area` route, and
executable `next` while unfinished. Do not pre-create speculative trees, phase
checklists, or child catalogs.

A task that coordinates children states its own outcome and concise `Done when` criteria. Its `next` is one concrete frontier action, or one wikilinked direct child at the current frontier; it is not a progress roll-up or a list of children. Change that frontier deliberately as evidence changes, without adding reciprocal edges or updating every child.

Roll up from evidence, not child counts. A parent's result records the evidence that its own outcome and `Done when` criteria are met. Resolve it only when that evidence exists and every child created for that outcome is resolved or explicitly disposed; resolving children alone does not complete the parent. Keep the parent unfinished when its criteria, evidence, or a necessary child remain open.

## Dependency revisions and derived staleness

Pin only context-bearing dependency edges to the dependency revision last reconciled:

```markdown
Depends on [[DEF-auth-protocol]] at context_rev 7.
```

Do not pin navigation links such as `Parent`, `Indexes`, or casual `Related to` links. Child and backlink views are derived rather than stored.

A node is derived `Stale` when a dependency is missing, its current `context_rev` differs from the edge's pinned revision, or the dependency link lacks a revision pin. Do not add `stale` to the directory status or frontmatter. A semantic dependency change intentionally leaves dependents' pins unchanged so one exact backlink search identifies reconciliation work.

## Read and execute loop

For each immediate micro-step:

1. Read `nodes/index-map.md` only when orienting or when no direct node pointer was supplied.
2. Locate a known node with a filename search such as `find nodes -name 'TAS-101-*'`. Read its frontmatter and a short body preview first.
3. For every context-bearing dependency, read the dependency header and compare its `context_rev` with the pinned revision. Follow only mismatched or context-required pointers.
4. Groom a stale node before execution: reconcile its assumptions, update dependency pins, increment its local `context_rev` only if that reconciliation changes context its consumers need, and refresh `updated`.
5. Execute the smallest coherent unit. Update summary, next, evidence, status directory, context revision when applicable, and timestamp as required.

Never bulk-dump `nodes/` into context or open every result from a broad query. Filter and count in the shell, then open only the selected node or dependency fragments needed for the decision.

## Common queries

Adapt ID prefixes and paths to the vault's convention:

```sh
# Known item
find nodes -type f -name 'TAS-101-*'

# Unfinished tasks and blocked tasks
find nodes -type f -name 'TAS-*.md' | rg '/(active|proposed|blocked)/'
find nodes -type f -path '*/blocked/TAS-*.md'

# Highest actionable priority (also works when no active directory exists)
find nodes -type f -path '*/active/TAS-*.md' -exec rg -l '^priority: P0$' {} +

# Direct dependents and their pinned revisions
rg -n -F 'Depends on [[DEF-auth-protocol]] at context_rev ' nodes

# Exceptional lifecycle state
rg -l '^disposition: deprecated$' nodes

# Recently updated nodes
rg -H '^updated:' nodes | awk -F ': ' '{print $2 " " $1}' | sort -r | head -5

# Primary membership routes (hub membership is derived from these backlinks)
rg -n '^(Parent|Area) \[\[' nodes
```

Prefer counts or bounded results over printing thousands of paths. Direct backlink search is authoritative for explicit edges; transitive impact requires repeating the search through the returned dependents.

## Optional integrity check

For grooming or CI, an installed copy includes `scripts/graph-check.rb`. It is a portable, read-only check with no database, cache, daemon, or generated state:

```sh
ruby .agents/skills/knowledge-execution-graph/scripts/graph-check.rb nodes
```

Run it from the project root, passing the current vault's nodes directory when it is not `nodes`. It validates the current status-directory layout: node identity and links, required headers and lifecycle rules, canonical edges and frontiers, dependency-pin syntax and revision mismatch, primary-route reachability, and parent cycles. It is optional; ordinary graph work never depends on it.

## Mutation rules

- New nodes start at `context_rev: 1`. For serial or otherwise coordinator-controlled creation, use `find` to check for collisions before choosing an ID. In parallel, use the parallel ID allocation protocol: a local `find` detects collisions only and never reserves an ID.
- On every mutation, refresh only that node's `updated`. Increment its `context_rev` only for a consumer-relevant semantic change. Never update unrelated nodes or the index as bookkeeping.
- Change status by moving the unchanged filename between status directories and updating the same node's current content. Wikilinks use the basename and remain stable.
- When a distinct subtask or thought emerges, apply the decomposition and admission contracts before creating it, then put its one primary `Parent [[...]]` or `Area [[IDX-...]]` link on that node. Do not also add a `Child` or `Parent of` copy to the parent; its `next` may name only the one deliberate frontier child. Create a root hub only as an `IDX` node reached by `Indexes` from `index-map.md`; it has neither primary link.
- Use `blocked` only when execution cannot continue without missing input or an external state change. Record `Blocked by` and `Unblocks when` in a short `# Blocked` section; set `next` to a concrete unblock action when one exists.
- Use `resolved` only when the stated outcome is complete. For a coordinating task, verify its `Done when` criteria, outcome evidence, and created-child dispositions before resolving. Remove `next`, keep concise result evidence, and retain the node as history.
- For abandonment, deprecation, or supersession, move completed work to `resolved`, set the sparse `disposition`, and record any replacement link. Search for remaining backlinks before considering migration complete.
- Preserve unrelated user changes and existing vault conventions. Graph bookkeeping does not broaden authorization for code, external systems, or destructive actions.

## Node body

Frontmatter carries the one-line outcome and executable next action. Use body headings only for additional current information:

```markdown
# Context

Depends on [[DEF-auth-protocol]] at context_rev 7.

# Blocked

Blocked by the service owner decision. Unblocks when the owner selects an expiry rule.

# Outcome

Reject expired authentication grants.

# Done when

The boundary test demonstrates the expiry rule.

# Result

Boundary tests pass against the selected rule.
```

Omit empty headings. Definitions put detail under `# Invariant`; thoughts capture the question and conclusion; index nodes contain pointers rather than copied content. A `DEC` node records a settled choice under concise `# Decision`, `# Rationale`, and `# Consequences` sections. Resolve it when the choice is formed; it remains current knowledge until explicitly deprecated or superseded.

## Status output

Report graph lists in compact TOON, not JSON or narrative tables. Use only fields needed for the decision:

```text
nodes{id,status,priority,context_rev}: TAS-101,active,P1,3 | DEF-auth,resolved,,7
```

State zero results explicitly. Add a short `stale:` or `help:` line only when it changes the next action.
