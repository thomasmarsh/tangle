---
name: tangle
description: Manage engineering work in a local Markdown vault as atomic, wikilink-connected nodes with an authoritative status field and dependency-revision checks. Use when the user invokes this skill or asks to plan, track, or execute work through a Markdown knowledge graph; do not use for ordinary Markdown editing.
---

# Tangle

Markdown is the durable, human-visible authority: keep the vault directly editable and Obsidian-compatible. The installed `tangle` command answers graph questions, maintains its own derived index, and runs optional same-host coordination, but it never replaces Markdown as truth: local coordination state is derived and disposable. Read the topical reference named below before the first conditional workflow it covers; `tangle help TOPIC` prints the same installed Markdown.

## Vault shape

- Root is the directory containing `.tangle/index-map.md`, and `./.tangle` is the default vault.
- A canonical node is one Markdown file under `.tangle/canonical/<suffix>/`; its frontmatter `status` field is authoritative. `.tangle/project-id` holds the clone-stable `prj-` project UID.
- Names are `<id>-<short-slug>.md`; a new `tas`/`tho`/`def`/`dec`/`idx`/`fbk` id is its lowercase type prefix plus 128 bits as 26 lowercase Crockford Base32 characters, so the basename is the immutable identity. Never restate id or status in frontmatter beyond the authoritative `status` field.
- Legacy uppercase numeric ids and `.tangle/proposed/`, `.tangle/active/`, `.tangle/blocked/`, `.tangle/resolved/` status-directory nodes stay readable during a versioned compatibility window; `tangle stationarize` retires that layout once per vault, and new writes use the stationary store.
- Store each relationship in one canonical direction — `Parent` on the child, `Area` on the assigned node, `Depends on` on the consumer, `Superseded by` on the obsolete node, `Indexes` on `index-map.md` — and derive the reverse views by search; never store reciprocal edges.

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

- Start `context_rev` at `1`; increment it only when a change could alter an assumption, decision, invariant, interface, or other context a pinned consumer must reread. Refresh `updated` to the current UTC ISO-8601 time on every mutation, and never bump `context_rev` for cosmetic edits, history, status changes, or `priority`/`next` changes. Clearing a blocker is exactly that status change with a `next` change, so it never bumps `context_rev`: a consumer detects readiness from the authoritative `status` field, and a semantic change made in the same edit still bumps it. Every writer reads the actual host clock when it refreshes `updated` — the real time, not an estimated or rounded value. A coordinator stamps the host clock at handoff — the real host clock time, not a rounded or estimated value — so it hands no worker a future `updated` to clamp; a worker refreshing an inherited `updated` ahead of the host clock uses `max(now, previous updated)` and notes the clamp rather than moving it backwards.
- `priority` is optional, task-only `P0`-`P3`. `next` is required for proposed/active tasks, holds a blocked task's unblock action, and is omitted from resolved tasks. `disposition` is optional and sparse: `abandoned`, `deprecated`, or `superseded`, with the replacement link in the body.

## Admission and the node boundary

Admit a node only when its conclusion or executable state is likely to change a future decision or action. Never admit conversation transcripts, tool-call logs, routine narration or status, duplicate source material, or observations with no foreseeable decision or action value. Tangle is durable execution memory, not a worklog: work planned to be committed and finished within one session needs no node, because Git already records it.

Prefer updating the existing node when new information advances the same outcome, question, component, decision, or defect. Independent resumability is necessary but not sufficient: a distinct node must also retain durable execution-memory value that will likely change a later decision or action or materially reduce future resumption cost. Agent boundaries, write-set boundaries, failed checks, mechanical cleanup, routine verification, and handoffs alone never qualify. A mechanical change with no independently resumable outcome belongs in the enclosing node's `next` or result, or carries a `Refs:` footer naming that node. A fresh worker may continue the same graph node; agents and nodes are not one-to-one.

One node owns one durable outcome or decision, not an estimated session, commit, agent assignment, or amount of code: one node may span sessions, and one session may advance several frontier nodes. Reassess a boundary when execution reveals new evidence, or when the authored `# Done when` already names outcomes with independent completion evidence: split when an outcome can be accepted, verified, consumed, blocked, or resumed independently and retains durable execution-memory value; consolidate adjacent nodes when they share one outcome, completion evidence, and rollback boundary and neither retains independent future value, continuing the stronger owner and preserving or reconciling backlinks. Do neither merely because a session ended, an agent changed, or the work size shifted. A just-in-time slice in a warnings-as-errors workspace is not independently acceptable when it lands a type or trait before its consumer: the slice includes a live consumer, or the node's `next` names that consumer as a mandatory companion. The on-demand commands `tangle similar --file PATH`, `tangle digest NODE`, and, when the optional semantic capability is installed, `tangle clusters`, are advisory support only, used after boundary evidence appears; no checker or command claims semantic authority over scope, and `tangle check` validates graph structure only.

## Status, next, and roll-up

`proposed` is ready but not yet at the frontier; `active` is being worked; `blocked` needs input or state no node in this vault owns; `resolved` is complete. Change status by editing the authoritative `status` field in place, so wikilinks and history stay stable; land that edit and the node's `# Result`/`# Resolution` body change in the same commit. A settled `DEF` or `DEC` is `resolved`; while its invariant or decision is unsettled it stays `proposed`.

`# Focus`, `priority`, and `active` are advisory navigation, never a work claim. A node's `next` is the one deliberate frontier route: the only accepted forms are a plain action sentence, `Do X.`, or a single `[[direct-child]]` link. A `next` written as an action sentence must contain no wikilink: `tangle check` names the token it treated as the frontier route. Naming multiple children or a non-child fails the graph check. Resolve a coordinating task only when its own `Done when` criteria are met and every child is resolved or disposed; resolving children alone does not complete the parent.

`blocked` and `proposed` are not interchangeable. Use `blocked` only for input or state that no node in this vault owns, including prerequisite plan text with no owning node, with a short `# Blocked` section and a concrete `next` when one exists. Use `proposed` for work that is ready to start but not yet at the frontier, including a child gated on a sibling decision: that decision is in the graph and will resolve there. Once a node owns the plan text, the same gate is a sibling dependency and the node is `proposed`.

A frontier node whose `# Done when` cannot be met in one session is advanced by the smallest coherent slice, not held back and not overrun: record the completed slice, the remaining scope, and its evidence in the body, set `next` to the first remaining action, and leave the node `proposed` or `active`. Unblocking is not completing: clearing a blocker returns the node to `proposed` with its first remaining action as `next`, never to `resolved`. A slice is a unit of execution, not a split trigger or a sizing ritual.

A cross-cutting compatibility migration exposes an ordered set of milestones —
reader, writer, dry-run, apply/recovery, and benchmark — each independently
acceptable with its own acceptance/verification; a broad migration task must
name them so its `next` never leaves the first implementation slice ambiguous.

## Reachability and the frontier

`index-map.md` routes to durable `IDX` root hubs via `Indexes`; a hub has no `Parent`/`Area` and does not list members. Every other node has exactly one primary, unpinned `Parent` or `Area` link that must reach a hub. An unfinished node that cannot reach a hub or a deliberate `# Focus` pointer is an orphan and a graph-integrity failure. Derive hub membership with an exact `Parent`/`Area` backlink search; never copy it into a hub or the index.

To find the frontier, derive hub members and follow each coordinating node's `next`; the `next` route, not `# Focus` or `priority`, names the one deliberate frontier child. The direct-answer verbs `tangle frontier`, `tangle next --rank`, and `tangle orient` return frontier candidates instead — every unfinished node with an action `next`. A user-requested plan pre-creates its children as `proposed`, so a sequenced sibling carries its own action `next` and is reported beside the deliberate child. Resolve the candidate list through the coordinator before executing: keep only the candidate its coordinating parent's `next` route names.

## Dependency readiness

Confirm each pinned dependency is `resolved` before executing. Pin context-bearing dependencies only, in the form `Depends on [[DEF-auth-protocol]] at context_rev 7.` where the pin terminates its line; record an unresolved target as a gate instead — `Gated on [[DEF-auth-protocol]].` in `# Context` — leave the consumer `proposed`, and never pin the gate. A pinned dependency whose target is not `resolved` is a checker failure that `--allow-stale` does not relax.

Load **dependencies** (`tangle help dependencies`) for staleness, the semantic-revision bump shape and its sanctioned staged-staleness gate, reconciliation ownership, and reversal versus supersession.

## Mutation rules

- New ids come from cryptographic entropy at admission, so parallel writers never collide and share no sequence or reservation. For a legacy numeric prefix during the compatibility window only, `tangle allocate PREFIX [COUNT]` reserves ids and a local `find` is collision detection only. A discarded `tangle allocate` burns its id permanently: there is no release or reclaim, and `tangle reservations` lists each prefix's reserved-but-unwritten ids.
- Refresh only the mutated node's `updated`; increment `context_rev` only for a consumer-relevant semantic change. Never edit unrelated nodes or the index as bookkeeping.
- Give each node one primary `Parent [[...]]` or `Area [[IDX-...]]` link; do not add a `Child`/`Parent of` copy to the parent.
- `resolved` only when the outcome is complete; for a coordinating task verify `Done when`, evidence, and child dispositions first. Remove `next` and keep concise evidence.
- Advancing a coordinating parent's `next` after its frontier child resolves is part of that resolution, so the resolving worker owns that edit: refresh the parent's `updated` and leave its `context_rev` unchanged, because `next` is navigation. A handoff whose write set names the parent — or its `next` line — folds that advance into the child's resolution commit. A handoff whose write set excludes the parent cannot make that edit: the child's resolution commit completes the worker's slice and the pending advance is its handoff action — name the parent and the resolved child, do not edit outside the set, and check with `tangle check --allow-pending-advance PARENT`, which sanctions that declared pending advance. That window is the multi-writer transient, not a failed slice; a genuine stale route — an unfinished node's `next` naming a resolved node, which the plain `tangle check` flags as `next-resolved-node` — keeps failing and the coordinator clears it at integration.
- Resolving a frontier knowledge node (`THO`/`DEF`/`DEC`) is to answer the question and resolve it like any other frontier node; in the same change advance the coordinating parent's `next` to the next deliberate frontier child.
- Graph bookkeeping never broadens authorization for code, external systems, or destructive actions.
- The derived index maintains itself on every interaction, so no client keeps it current by hand; `tangle index` exists only to repair or rebuild it from Markdown.

## Read and execute loop

1. Read `.tangle/index-map.md` when orienting or when no direct node pointer was supplied.
2. With no pointer, run `tangle frontier` for frontier candidates and resolve the candidate list through the coordinator as above. `# Focus`, `priority`, and `active` are not the frontier.
3. Locate a known node with a filename search such as `find .tangle -name 'TAS-101-*'`.
4. For each context-bearing dependency, compare its header `context_rev` with the pin and confirm it is `resolved`; follow only mismatched, blocking, or required pointers.
5. Execute the smallest coherent unit and update summary, `next`, evidence, status, `context_rev`, and `updated`.

A recorded premise or `# Outcome` statement that the code contradicts is a factual correction, not a scope change: record the corrected state and the evidence that shows it in `# Result`, and bump `context_rev` only when a pinned consumer relied on the premise. Escalate instead of correcting when the correction would change the declared scope, outcome, or `Done when`. When the coordinating parent repeats the same wrong premise, the worker that found it reports the correction with evidence and the coordinator, which owns the shared parent, edits the parent; the worker edits only the node it owns.

One orientation pass is enough. Never bulk-dump `.tangle/`; filter and count in the shell, then open only the fragments needed. If a search returns nothing, report it rather than retrying with different flags. Report graph lists in compact TOON with only the fields needed, state zero results explicitly, and name the resolved node, new status, and advanced frontier in a completion report.

## References and command help

Run `tangle <verb> --help` for command syntax. Conditional workflow prose is installed Markdown printed by `tangle help TOPIC`. Load only the reference the current operation requires.

- **change-intake** — `tangle help change-intake` for asynchronous contributions ([references/change-intake.md](references/change-intake.md)).
- **coordination** — `tangle help coordination` before claims, leases, parallel worktrees, handoff, integration, or multi-host work ([references/coordination.md](references/coordination.md)).
- **dependencies** — `tangle help dependencies` before pinning, gating, bumping `context_rev`, staged-staleness commits, reversal, supersession, or regenerating a resolved node's derived artifact ([references/dependencies.md](references/dependencies.md)).
- **authoring** — `tangle help authoring` before writing node bodies, feedback nodes, capture commands, vault layout or migration, or decomposition and roll-up detail ([references/authoring.md](references/authoring.md)).

`tangle --help` stays the short command and topic index.
