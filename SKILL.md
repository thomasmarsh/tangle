---
name: knowledge-execution-graph
description: Manage engineering work in a local Markdown vault as atomic, wikilink-connected nodes with indexed revisions and dependency-staleness checks. Use when the user invokes this skill or asks to plan, track, or execute work through a Markdown knowledge graph; do not use for ordinary Markdown editing.
---

# Knowledge Execution Graph

Use the vault as a low-overhead execution graph. Keep planning, decisions, definitions, component notes, bug traces, and task state durable without loading unrelated context.

## Vault contract

- Treat the directory containing `index-map.md` as the vault root. Store graph nodes in `nodes/`.
- Keep each node about one task, thought thread, component definition, file index, or bug trace. Split a file when it develops independently actionable topics.
- Name nodes `<ID>-<short-slug>.md`, preserving the vault's existing ID convention. Use prefixes such as `TAS`, `THO`, `DEF`, `IDX`, and `BUG`; represent bug work with `type: task` because `bug` is not a metadata type.
- Connect nodes with Markdown wikilinks such as `[[TAS-101-auth-leak]]`. Prefix every link with its relationship, for example `Depends on`, `Implements`, `Parent`, or `Indexes`.
- Keep prose terse. Store conclusions and executable state, not transcripts or expansive reasoning.

Every node, including `index-map.md`, must begin with exactly this metadata shape:

```yaml
---
id: TAS-101
type: task
status: active
seq: 42
mtime: 2026-09-09T20:15:00Z
---
```

Allowed values:

- `type`: `task`, `thought`, `definition`, or `index`
- `status`: `proposed`, `active`, `blocked`, or `resolved`

Keep `id` stable. Write `mtime` as the current UTC ISO-8601 timestamp. Treat `seq` as a vault-wide revision: each file write receives the next integer, so sequence comparisons across nodes are meaningful.

## Index contract

`index-map.md` is the entry point and sequence ledger. Its body contains a compact row for every node with at least `id`, wikilink, `type`, `status`, `seq`, and `mtime`. Update it after every node mutation and assign the index update its own next sequence number.

When bootstrapping an empty vault, create only `nodes/` and `index-map.md`; add nodes as work requires them. Never create broad catch-all planning files.

## Read and execute loop

For each immediate micro-step:

1. Locate the relevant row in `index-map.md`. If given a direct entry pointer, inspect that pointer plus its index row.
2. Read the target node's frontmatter and a short body preview first. Use targeted search for wikilinks or headings; read the full node only when the preview is insufficient.
3. Classify outgoing context-bearing links such as `Depends on`, `Implements`, `Requires`, or `Governed by` as dependencies. Do not treat navigation links such as `Parent`, `Child`, `Backlink`, or `Indexes` as dependencies.
4. Compare each dependency's indexed `seq` and `mtime` with the target. If a dependency is newer, missing from the index, or disagrees with its index row, report the target as derived `Stale` state. Do not add `stale` to `status` or frontmatter.
5. Follow only the stale or context-required pointers. Repeat the check recursively and stop traversing once the immediate micro-step has enough current context.
6. Groom a stale node before executing it: reconcile its assumptions, links, and next action with the newer dependencies, then bump its `seq` and `mtime` and update the index.
7. Execute the smallest coherent unit of work. Update the node's result and status, bump metadata again, then update the index.

Never bulk-read `nodes/`, recursively dump the vault, or open every linked file. Prefer frontmatter, index rows, heading searches, and bounded excerpts. A full read is appropriate only for the node currently being executed or a dependency whose relevant fragment cannot be located cheaply.

## Mutation rules

- Before any write, reserve the next `seq` as one greater than the largest sequence recorded by the index and its own frontmatter.
- Give every written file a distinct sequence in actual write order. Update `index-map.md` last so it records the final state of the transaction.
- On every node write, refresh both `seq` and `mtime`, even for metadata-only or link-only changes.
- When a distinct subtask or thought emerges, create a new atomic node. Link it from the parent with a qualified relationship and link back with `Parent [[...]]`; then groom the parent after creating the child.
- Mark `blocked` only when execution cannot continue without missing input or an external state change. Record the blocker and the exact unblocking condition.
- Mark `resolved` only when the node's stated outcome is complete. Keep resolved nodes indexed; do not delete execution history unless the user asks.
- Preserve unrelated user changes and existing vault conventions. Graph bookkeeping does not broaden authorization for code, external systems, or destructive actions.

## Node body

Use only headings that carry current information. A typical task needs:

```markdown
# Outcome

One concrete desired result.

# Context

Depends on [[DEF-auth-protocol]].

# Next

One executable micro-step.

# Result

Current evidence or completed outcome.
```

Omit empty headings. Definitions should state the invariant or interface; thoughts should capture the question and conclusion; index nodes should contain pointers rather than copied content.

## Status output

Report graph lists in compact TOON, not JSON or narrative tables. Use the user-facing schema requested by the vault, for example:

```text
nodes{id,type,status,seq}: TAS-101,task,active,42 | DEF-auth,definition,resolved,12
```

Include only fields needed for the decision at hand. State zero results explicitly. Add a short `stale:` or `help:` line only when it changes the next action.
