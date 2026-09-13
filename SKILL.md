---
name: braintree
description: Manage engineering work in a local Markdown vault as atomic, wikilink-connected nodes with authoritative status directories and dependency-revision checks. Use when the user invokes this skill or asks to plan, track, or execute work through a Markdown knowledge graph; do not use for ordinary Markdown editing.
---

# Braintree

Markdown is the durable, human-visible authority: keep the vault directly editable and Obsidian-compatible. The installed `braintree` command answers graph questions and runs optional same-host coordination, but it never replaces Markdown as truth: the sidecar is authoritative only for local operational coordination, and no worker reads or writes it directly. Read the topical reference named below before the first conditional workflow it covers; `braintree help TOPIC` prints the same installed Markdown.

## Vault shape

- Root is the directory containing `.braintree/index-map.md`.
- Each node lives in exactly one fixed status directory: `.braintree/proposed/`, `.braintree/active/`, `.braintree/blocked/`, or `.braintree/resolved/`. A status directory exists only once a node has that status; no empty directory is required.
- `braintree` resolves the vault at `./.braintree` by default; `BT_NODES_DIR` or an explicit directory operand overrides it. A legacy `nodes/` vault is migrated to `.braintree/` in place by `braintree migrate` or by the default resolver, leaving the Markdown bytes unchanged.
- Names are `<ID>-<short-slug>.md`; `TAS`/`THO`/`DEF`/`IDX`/`FBK` express type. Filename supplies ID/type, directory supplies status; never duplicate them in frontmatter.
- Store each relationship in one canonical direction: `Parent` on the child, `Area` on the assigned node, `Depends on` on the consumer, `Superseded by` on the obsolete node, `Indexes` on `index-map.md`. Derive child, parent-of, indexed-by, and backlink views by search; never store reciprocal edges.

Required frontmatter:

```yaml
---
context_rev: 3
priority: P1
updated: 2026-09-10T01:30:00Z
summary: Reject expired authentication grants.
next: Add the failing boundary test.
---
```

- Start `context_rev` at `1`; it is a consumer-context revision, not an edit counter: increment it only when a change could alter an assumption, decision, invariant, interface, or other context a pinned consumer must reread. Refresh `updated` to the current UTC ISO-8601 time on every mutation, and never bump `context_rev` for cosmetic edits, history, status moves, or `priority`/`next` changes. A coordinator stamps the real UTC time at handoff, and a worker refreshing an inherited `updated` ahead of the host clock uses `max(now, previous updated)` and notes the clamp rather than moving it backwards.
- `priority` is optional, task-only `P0`-`P3`. `next` is required for proposed/active tasks, holds a blocked task's unblock action, and is omitted from resolved tasks. `disposition` is optional and sparse: `abandoned`, `deprecated`, or `superseded`, with the replacement link in the body.

## Admission and the node boundary

Admit a node only when its conclusion or executable state is likely to change a future decision or action. Never admit conversation transcripts, tool-call logs, routine narration or status, duplicate source material, or observations with no foreseeable decision or action value.

Prefer updating the existing node when new information advances the same outcome, question, component, decision, or defect. Independent resumability is necessary but not sufficient: a distinct node must also retain durable execution-memory value that will likely change a later decision or action or materially reduce future resumption cost. Agent boundaries, exclusive write-set boundaries, failed checks, incidental or mechanical cleanup, routine verification, and handoffs alone never qualify. A mechanical change with no independently resumable outcome belongs in the enclosing node's `next` or result, or carries a `Refs:` footer naming that node. A fresh worker may continue the same graph node; agents and nodes are not one-to-one.

One node owns one durable outcome or decision, not an estimated session, commit, agent assignment, or amount of code: one node may span sessions, and one session may advance several frontier nodes. Reassess a boundary when execution reveals new evidence, not through a mandatory per-node sizing pass: split when execution reveals another outcome that can be accepted, verified, consumed, blocked, or resumed independently and that retains durable execution-memory value; consolidate adjacent nodes when they share one outcome, completion evidence, and rollback boundary and neither retains independent future value, continuing the stronger owner and preserving or reconciling backlinks. Do neither merely because a session ended, an agent changed, several commits landed, or the work is larger or smaller than expected. The on-demand commands `braintree similar --file PATH`, `braintree digest NODE`, and, when the optional semantic capability is installed, `braintree clusters`, are advisory support only, used after boundary evidence appears; no checker or command claims semantic authority over scope, and `braintree check` validates graph structure only.

## Status, next, and roll-up

`proposed` is ready but not yet at the frontier; `active` is being worked; `blocked` needs input or state no node in this vault owns, such as a credential or an external approval; `resolved` is complete. Change status by moving the unchanged filename between those directories, so wikilinks keep the stable basename. Stage that move and the node's `# Result`/`# Resolution` body edit in the same commit: `git mv` can stage the pre-edit blob, so `git add` the destination after the move, and make the move the last step before committing that node. A settled `DEF` or `DEC` is `resolved`; while its invariant or decision is still unsettled it stays `proposed`.

`# Focus`, `priority`, and `active` are advisory navigation, never a work claim. A node's `next` is the one deliberate frontier route: the only accepted forms are a plain action sentence, `Do X.`, or a single `[[direct-child]]` link. Naming multiple children or a non-child fails the graph check. Resolve a coordinating task only when its own `Done when` criteria are met and every child is resolved or disposed; resolving children alone does not complete the parent.

`blocked` and `proposed` are not interchangeable. Use `blocked` only for input or state that no node in this vault owns, including prerequisite plan text with no owning node, with a short `# Blocked` section and a concrete `next` when one exists. Use `proposed` for work that is ready to start but not yet at the frontier, including a child gated on a sibling decision: that decision is in the graph and will resolve there. Once a node owns the plan text, the same gate is a sibling dependency and the node is `proposed`.

## Reachability and the frontier

`index-map.md` routes to durable `IDX` root hubs via `Indexes`; a hub has no `Parent`/`Area` and does not list members. Every other node has exactly one primary, unpinned `Parent` or `Area` link that must reach a hub. An unfinished node that cannot reach a hub or a deliberate `# Focus` pointer is an orphan and a graph-integrity failure. Derive hub membership with an exact `Parent`/`Area` backlink search; never copy it into a hub or the index.

To find the frontier, derive hub members and follow each coordinating node's `next`; the `next` route, not `# Focus` or `priority`, names the one deliberate frontier child. The direct-answer verbs `braintree frontier`, `braintree next --rank`, and `braintree orient` return frontier candidates instead — every unfinished node whose `next` is an action, a superset of the frontier. A user-requested plan pre-creates its children as `proposed`, so a sequenced sibling carries its own action `next` and is reported beside the deliberate child. Resolve the candidate list through the coordinator before executing: keep only the candidate its coordinating parent's `next` route names, because a candidate whose parent's `next` names a different node is not yet at the frontier.

## Dependency readiness

Confirm each pinned dependency is `resolved` before executing. Pin context-bearing dependencies only, in the form `Depends on [[DEF-auth-protocol]] at context_rev 7.` where the pin terminates its line; a dependency whose target is not yet `resolved` has no consumable context to pin, so record it as a gate instead — `Gated on [[DEF-auth-protocol]].` in `# Context` — leave the node `proposed`, and never pin the gate; replace the gate with the pinned `Depends on` edge once the target resolves. A pinned dependency whose target is `proposed`, `active`, or `blocked` is a checker failure that `--allow-stale` does not relax.

Load **dependencies** (`braintree help dependencies`) for staleness, the semantic-revision bump shape and its sanctioned staged-staleness gate, reconciliation ownership, and reversal versus supersession.

## Mutation rules

- Use `find` (or `braintree allocate PREFIX` in parallel) to avoid ID collisions; a local `find` detects collisions only and never reserves an ID.
- Refresh only the mutated node's `updated`; increment `context_rev` only for a consumer-relevant semantic change. Never edit unrelated nodes or the index as bookkeeping.
- Give each node one primary `Parent [[...]]` or `Area [[IDX-...]]` link; do not add a `Child`/`Parent of` copy to the parent.
- `resolved` only when the outcome is complete; for a coordinating task verify `Done when`, evidence, and child dispositions first. Remove `next` and keep concise evidence.
- Advancing a coordinating parent's `next` after its frontier child resolves is part of that resolution, so the resolving worker owns that edit: refresh the parent's `updated` and leave its `context_rev` unchanged, because `next` is navigation. A handoff whose write set excludes the parent must name the parent (or its `next`) in the write set; otherwise the coordinator owns the advance, and the worker reports the stale route — an unfinished node's `next` naming a resolved node, which `braintree check` flags — as a handoff action.
- Resolving a frontier knowledge node (`THO`/`DEF`/`DEC`) is to answer the question and resolve it like any other frontier node; in the same change advance the coordinating parent's `next` to the next deliberate frontier child.
- Graph bookkeeping never broadens authorization for code, external systems, or destructive actions.

## Read and execute loop

1. Read `.braintree/index-map.md` when orienting or when no direct node pointer was supplied.
2. With no pointer, run `braintree frontier` for frontier candidates and resolve the candidate list through the coordinator as above. `# Focus`, `priority`, and `active` are not the frontier.
3. Locate a known node with a filename search such as `find .braintree -name 'TAS-101-*'`.
4. For each context-bearing dependency, compare its header `context_rev` with the pin and confirm it is `resolved`; follow only mismatched, blocking, or required pointers.
5. Execute the smallest coherent unit and update summary, `next`, evidence, status, `context_rev`, and `updated`.

One orientation pass is enough. Never bulk-dump `.braintree/`; filter and count in the shell, then open only the fragments needed. If a search returns nothing, report it rather than retrying with different flags. Report graph lists in compact TOON with only the fields needed, state zero results explicitly, and name the resolved node, new status, and advanced frontier in a completion report.

## References and command help

Command syntax lives in per-verb help: run `braintree <verb> --help` for a verb's operands, output fields, exit meanings, and command-specific hazards. Conditional workflow prose lives in the installed references, readable as Markdown and printed by `braintree help TOPIC`. Load only the reference the current operation requires.

- **coordination** — `braintree help coordination` before claims, leases, parallel worktrees, handoff, integration, or multi-host work ([references/coordination.md](references/coordination.md)).
- **dependencies** — `braintree help dependencies` before pinning, gating, bumping `context_rev`, staged-staleness commits, or reversal and supersession ([references/dependencies.md](references/dependencies.md)).
- **authoring** — `braintree help authoring` before writing node bodies, feedback nodes, capture commands, or decomposition and roll-up detail ([references/authoring.md](references/authoring.md)).

`braintree --help` stays the short command and topic index.
