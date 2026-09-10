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
- Keep prose terse. Store conclusions and executable state, not transcripts or expansive reasoning.

The filename is authoritative for ID and type; the containing directory is authoritative for status. Do not duplicate those values in frontmatter.

Every node begins with compact frontmatter:

```yaml
---
rev: 3
priority: P1
updated: 2026-09-10T01:30:00Z
summary: Reject expired authentication grants.
next: Add the failing boundary test.
---
```

- `rev`, `updated`, and `summary` are required. Start `rev` at `1` and increment it on every write to that node. Use the current UTC ISO-8601 time for `updated`.
- `priority` is optional and normally task-only. Use `P0`, `P1`, `P2`, or `P3`; absence means unranked.
- `next` is required for proposed and active tasks. For a blocked task, use it for the concrete unblock action when one exists; otherwise omit it. Always omit it from resolved nodes.
- `disposition` is optional. Add it only when the value is `abandoned`, `deprecated`, or `superseded`; do not store `current` or empty lifecycle fields.
- Put a replacement link such as `Superseded by [[TAS-102-new-path]]` in the body rather than duplicating it in frontmatter.
- Do not add created timestamps, owners, labels, dependency arrays, or other fields unless a demonstrated local workflow earns their ongoing cost.

## Index contract

`nodes/index-map.md` is a small intent and routing document, not a node catalog or revision ledger. It may contain:

- a short `# Focus` list of deliberate entry pointers;
- durable area or component entry pointers; and
- tested, trivial query recipes.

Never copy every node's status, priority, timestamp, revision, or summary into the index. Node mutations do not update the index. Update it only when project intent, navigation, or a query contract changes. A focus pointer is advisory: validate its target's status and header before acting.

When bootstrapping an empty vault, create `nodes/index-map.md`, the needed status directory, and the first node at `rev: 1`. Do not create broad catch-all planning files.

## Dependency revisions and derived staleness

Pin only context-bearing dependency edges to the dependency revision last reconciled:

```markdown
Depends on [[DEF-auth-protocol]] at rev 7.
```

Do not pin navigation links such as `Parent`, `Child`, `Backlink`, or `Indexes`, or casual `Related to` links.

A node is derived `Stale` when a dependency is missing, its current `rev` differs from the edge's pinned revision, or the dependency link lacks a revision pin. Do not add `stale` to the directory status or frontmatter. A changed dependency intentionally leaves dependents' pins unchanged so one exact backlink search identifies reconciliation work.

## Read and execute loop

For each immediate micro-step:

1. Read `nodes/index-map.md` only when orienting or when no direct node pointer was supplied.
2. Locate a known node with a filename search such as `find nodes -name 'TAS-101-*'`. Read its frontmatter and a short body preview first.
3. For every context-bearing dependency, read the dependency header and compare its `rev` with the pinned edge revision. Follow only mismatched or context-required pointers.
4. Groom a stale node before execution: reconcile its assumptions, update dependency pins, increment its local `rev`, and refresh `updated`.
5. Execute the smallest coherent unit. Update summary, next, evidence, status directory, local revision, and timestamp as required.

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
rg -n -F 'Depends on [[DEF-auth-protocol]] at rev ' nodes

# Exceptional lifecycle state
rg -l '^disposition: deprecated$' nodes

# Recently updated nodes
rg -H '^updated:' nodes | awk -F ': ' '{print $2 " " $1}' | sort -r | head -5
```

Prefer counts or bounded results over printing thousands of paths. Direct backlink search is authoritative for explicit edges; transitive impact requires repeating the search through the returned dependents.

## Mutation rules

- New nodes start at `rev: 1`. Before choosing an ID, use `find` to check for collisions; file-only numeric allocation is not atomic under concurrent creation.
- On every write, increment only that node's `rev` and refresh `updated`. Never update unrelated nodes or the index as bookkeeping.
- Change status by moving the unchanged filename between status directories and updating the same node's current content. Wikilinks use the basename and remain stable.
- When a distinct subtask or thought emerges, create a new atomic node. Link it from the parent with a qualified relationship and link back with `Parent [[...]]`.
- Use `blocked` only when execution cannot continue without missing input or an external state change. Record `Blocked by` and `Unblocks when` in a short `# Blocked` section; set `next` to a concrete unblock action when one exists.
- Use `resolved` only when the stated outcome is complete. Remove `next`, keep concise result evidence, and retain the node as history.
- For abandonment, deprecation, or supersession, move completed work to `resolved`, set the sparse `disposition`, and record any replacement link. Search for remaining backlinks before considering migration complete.
- Preserve unrelated user changes and existing vault conventions. Graph bookkeeping does not broaden authorization for code, external systems, or destructive actions.

## Node body

Frontmatter carries the one-line outcome and executable next action. Use body headings only for additional current information:

```markdown
# Context

Depends on [[DEF-auth-protocol]] at rev 7.

# Blocked

Blocked by the service owner decision. Unblocks when the owner selects an expiry rule.

# Result

Boundary tests pass against the selected rule.
```

Omit empty headings. Definitions put detail under `# Invariant`; thoughts capture the question and conclusion; index nodes contain pointers rather than copied content.

## Status output

Report graph lists in compact TOON, not JSON or narrative tables. Use only fields needed for the decision:

```text
nodes{id,status,priority,rev}: TAS-101,active,P1,3 | DEF-auth,resolved,,7
```

State zero results explicitly. Add a short `stale:` or `help:` line only when it changes the next action.
