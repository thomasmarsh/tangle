---
name: braintree
description: Manage engineering work in a local Markdown vault as atomic, wikilink-connected nodes with authoritative status directories and dependency-revision checks. Use when the user invokes this skill or asks to plan, track, or execute work through a Markdown knowledge graph; do not use for ordinary Markdown editing.
---

# Braintree

Markdown is the durable, human-visible authority: keep the vault directly editable and Obsidian-compatible.

## Hybrid sidecar contract

Use the installed `bt` command for graph indexes and live coordination: `uv run --project .agents/skills/braintree --frozen bt ...` (`.claude/skills/braintree` for Claude, `.pi/skills/braintree` for pi). Do not have workers read or write SQLite directly. The sidecar is an untracked external SQLite database keyed by the Git common directory and shared by all worktrees; `BT_SIDECAR_DIR`/`BT_PROJECT_ID` override it for tests.

- Markdown stays authoritative; SQLite is authoritative only for local operational coordination.
- `bt reindex [nodes]` rebuilds derived node, edge, content-hash, backlink, stale-pin, and FTS data from Markdown; `bt search`, `bt backlinks`, and `bt stale` reconcile first.
- `bt allocate PREFIX` atomically reserves an ID; `bt claim NODE AGENT --base-hash HASH [--lease-seconds N]` acquires or renews a lease, and `bt release NODE AGENT --base-hash HASH` releases it. The release hash must be the starting hash recorded by the claim: a hash or owner mismatch fails non-zero and names the cause, while `no-op` means the node holds no unexpired lease.
- `bt hash NODE` prints the base hash a claim records: the SHA-256 hex digest of the node file's raw UTF-8 bytes, frontmatter included. Get it from `bt hash` rather than reimplementing the algorithm, and pass that same starting value to `bt claim` and `bt release`.
- Run `bt init` before coordinated work. Loss of the database may lose claims and indexes but never durable graph knowledge; recover with `bt init` then `bt reindex`.
- The sidecar is for concurrent processes on one host and a local filesystem; it refuses a network-mounted location unless overridden. For multi-host coordination use a server database such as PostgreSQL; SQLite/WAL is not that service.
- Keep status directories and Markdown pointers. A stationary-path/status-in-database migration is deferred.

## Vault contract

- Root is the directory containing `nodes/index-map.md`.
- Each node lives in exactly one status directory: `nodes/proposed/`, `nodes/active/`, `nodes/blocked/`, or `nodes/resolved/`. Those four names are fixed, but a status directory is created on demand: it exists only once a node has that status, and no empty directory is required.
- Names are `<ID>-<short-slug>.md`; `TAS`/`THO`/`DEF`/`IDX`/`FBK` express type. Filename supplies ID/type, directory supplies status; do not duplicate them in frontmatter.
- Store each relationship in one canonical direction: put `Parent` on the child, `Area` on the assigned node, `Depends on` on the consumer, `Superseded by` on the obsolete node, and `Indexes` on `index-map.md` or another deliberate route. Derive child, parent-of, and backlink views by search; do not store them as reciprocal edges.

## Node admission

Admit a node only when its conclusion or executable state is likely to change a future decision or action. Do not admit conversation transcripts, tool-call logs, routine narration or status, duplicate source material, or observations with no foreseeable decision or action value.

Prefer updating the existing node when new information advances the same outcome, question, component, decision, or defect. Independent resumability is
necessary but not sufficient for a distinct node: it must also retain durable execution-memory value, likely to change a later decision or action or materially reduce future resumption cost. Agent boundaries, exclusive write-set boundaries, failed checks, incidental or mechanical cleanup, routine verification, and handoffs alone never qualify; keep them in the current node's `next`, result, evidence, or handoff. A fresh worker may continue the same graph
node; agents and nodes are not one-to-one.

A mechanical change with no independently resumable outcome — a one-line build, formatting, lint, or install fix — is not a node: record it in the enclosing node's `next` or result, or, when it needs its own commit, name that node in a `Refs:` footer.

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

- Start `context_rev` at `1`; it is a consumer-context revision, not an edit counter: increment it only when a change could alter an assumption, decision, invariant, interface, or other context a pinned consumer must reread. Refresh `updated` to the current UTC ISO-8601 time on every mutation.
- Do not increment `context_rev` for cosmetic edits, history additions, status moves, or priority/`next` changes.
- `priority` is optional, task-only `P0`-`P3`. `next` is required for proposed/active tasks, holds the unblock action for blocked tasks, and is omitted from resolved tasks.
- `disposition` is optional and sparse: `abandoned`, `deprecated`, or `superseded`. Put a replacement link in the body, not frontmatter.

## Index contract

`nodes/index-map.md` holds intent and routing, not state: a short `# Focus` list, durable area entry pointers, and tested query recipes. Never copy node status, priority, revision, timestamp, or summary into it. A focus pointer is advisory; validate its target before acting.

## Parallel worktree contract

`# Focus`, `priority`, and `active` status are advisory navigation, never a work claim. A coordinator assigns each worker a direct node path and an exclusive write set before work begins.

- One agent writes a node and its status path at a time. Shared parents, `index-map.md`, definitions, and root hubs are coordinator-owned unless their writes are explicitly serialized.
- A worktree is a snapshot, not global truth; workers do not assume unseen work or IDs are unclaimed.
- The coordinator integrates child evidence, reconciles upstream change, and alone resolves a coordinating parent after all required child work is integrated.
- For parallel creation, use `bt allocate PREFIX` to atomically reserve an ID; Coordinator preallocation or explicitly disjoint numeric ranges are valid offline alternatives. A local `find` checks for an existing collision only; it is never an ID reservation. Branch-local `owner` or claim metadata is insufficient because separate worktrees can make the same claim without seeing each other.

Before editing, a worker records the integration base and its assigned node path and write set, hashes its starting Markdown node with `bt hash`, and claims it with `bt claim`. A worktree slice is not a node boundary: a fresh worker may continue the assigned node. Keep the assigned node's content update and its status move coherent in one commit or handoff bundle. Before handoff, verify every changed, created, and moved path remains in that assigned write set, then release the matching claim. Report the base, touched paths, created paths, moved paths, dependency evidence, and test evidence to the coordinator.

Serial work uses the same discipline without branches: self-assign one node and write set, claim it, keep content and status coherent, run `uv run --project .agents/skills/braintree --frozen graph-check nodes`, and do not leave a resolved status move uncommitted.

The coordinator integrates worker branches one at a time. Never blindly auto-merge an upstream change to the assigned node or divergent status paths: reject that handoff or perform manual semantic reconciliation before integration. After each integration, run `uv run --project .agents/skills/braintree --frozen graph-check nodes`, use exact `rg -n -F 'Depends on [[ID]] at context_rev '` searches for every context-bearing dependency changed by that handoff, and reconcile stale consumers before their dependent execution. Resolve a coordinating parent only after its required child evidence has been integrated.

## Reachability contract

`index-map.md` routes to durable `IDX` root hubs via `Indexes`; a hub has no `Parent`/`Area` and does not list members. Every other node has exactly one primary, unpinned `Parent` or `Area` link that must reach a hub. To find the frontier, derive hub members and follow each coordinating node's `next`; the `next` route, not `# Focus` or `priority`, names the one deliberate frontier child. An unfinished node that cannot reach a hub or a deliberate `# Focus` pointer is an orphan and a graph-integrity failure. Derive hub membership with an exact `Parent`/`Area` backlink search; never copy it into a hub or the index.

## Decomposition and roll-up

Decompose just in time, only after the node-admission threshold, at a distinct independently resumable outcome, blocker, dependency, or verification boundary that also retains durable execution-memory value. A child states its outcome or decision, completion criterion, primary `Parent`/`Area` route, and executable `next`. Do not pre-create speculative trees. A user-requested plan is not speculative decomposition: create its children up front as `proposed` work and resolve or dispose each as reality arrives.

A direct child is a node whose primary `Parent` or `Area` is the current node. A coordinating task states its outcome and `Done when` criteria; its `next` is either one concrete frontier action or one wikilinked direct child at the current frontier, never a child list. The only accepted `next` forms are a plain action sentence, `Do X.`, or a single `[[direct-child]]` link; naming multiple children or a non-child fails the graph check. Roll up from evidence, not child counts; resolve only when its criteria are met and every child is resolved or disposed, since resolving children alone does not complete the parent.

`blocked` and `proposed` are not interchangeable. Use `blocked` only when the node needs input or state that no node in this vault owns, such as a credential or an external approval; use `proposed` for work that is ready to start but not yet at the frontier, including a child gated on a sibling decision. A proposed sibling is not blocked, because the decision it waits on is in the graph and will resolve there.

## Dependency revisions and staleness

Pin context-bearing dependencies only: `Depends on [[DEF-auth-protocol]] at context_rev 7.` The pin must terminate its line; trailing text after `at context_rev N.` is invalid. Do not pin navigation links. A node is `Stale` when a dependency is missing, its current `context_rev` differs from the pin, or the link lacks a pin; do not add `stale` to status or frontmatter. A semantic change leaves dependents' pins unchanged so one exact backlink search finds the reconciliation work. Confirm each pinned dependency is `resolved` before executing; resolution does not change `context_rev`, so completion is detected from the status directory. `graph-check` reports a pinned dependency whose target is `proposed`, `active`, or `blocked`, and `--allow-stale` does not relax that check because it only relaxes the revision equality.

The bump commit shape: commit the semantic `context_rev` bump with the bumped node alone, leaving pinned consumers stale on purpose so the exact backlink search finds them. That commit runs the sanctioned staged-staleness gate `graph-check --allow-stale nodes`, which still rejects a missing or malformed pin and relaxes only the revision equality; plain `graph-check nodes` remains the normal gate everywhere else. Reconciliation is separate work owned by each consumer: reread the dependency, update assumptions, reset the pin to the current `context_rev`, and pass the plain gate before that consumer executes. `--allow-stale` is sanctioned only for a deliberate staged-staleness commit: never use it to silence a pin you can reconcile now, and never leave a consumer stale across its own execution.

## Read and execute loop

1. Read `nodes/index-map.md` when orienting or when no direct node pointer was supplied.
2. With no pointer, run the `Frontier` recipe in `nodes/index-map.md` to list the current frontier directly: it returns the unfinished nodes whose `next` is an action rather than a `[[child]]` route, so a coordinating node's `next` target appears instead of the coordinator. Deriving a hub's members from `Parent`/`Area` backlinks and following each coordinating node's `next` reaches the same frontier. Validate the candidate's status and header exactly as a `# Focus` target. `# Focus`, `priority`, and `active` are not the frontier.
3. Locate a known node with a filename search such as `find nodes -name 'TAS-101-*'`.
4. For each context-bearing dependency, compare its header `context_rev` with the pin and confirm it is `resolved`; follow only mismatched, blocking, or required pointers.
5. Groom a stale node before execution: reconcile assumptions, update pins, and refresh `updated`.
6. Execute the smallest coherent unit and update summary, next, evidence, status, revision, and timestamp.

When the frontier is a knowledge node (`THO`/`DEF`/`DEC`), answer the question and resolve it like any other frontier node, and in the same change advance the coordinating parent's `next` to the next deliberate frontier child. That advance is part of resolving the frontier, not bookkeeping on an unrelated node: refresh the parent's `updated`, and leave its `context_rev` unchanged because `next` is navigation, not consumer-relevant semantics.

One orientation pass is enough. Never bulk-dump `nodes/`; filter and count in the shell, then open only the fragments needed. If a search returns nothing, report it rather than retrying with different flags.

## Common queries

```sh
rg --files-without-match '^next:.*\[\[' nodes/*/ 2>/dev/null | rg '/(active|proposed|blocked)/'  # frontier
find nodes -type f -name 'TAS-*.md' | rg '/(active|proposed|blocked)/'          # unfinished
find nodes -type f -path '*/active/TAS-*.md' -exec rg -l '^priority: P0$' {} +  # actionable P0
rg -n -F 'Depends on [[DEF-auth-protocol]] at context_rev ' nodes               # pinned dependents
rg -n '^(Parent|Area) \[\[' nodes                                               # primary routes
```

Prefer bounded results. Direct backlink search is authoritative for explicit edges; transitive impact repeats it through returned dependents.

## Integrity and sidecar commands

`graph-check` is a portable read-only Markdown validator needing no sidecar; `feedback-scan` is a portable read-only collector for external feedback; `bt` provides the optional hybrid index and same-host coordination:

```sh
uv run --project .agents/skills/braintree --frozen graph-check nodes
uv run --project .agents/skills/braintree --frozen feedback-scan /path/to/other-vault
uv run --project .agents/skills/braintree --frozen bt reindex nodes
uv run --project .agents/skills/braintree --frozen bt search 'authentication' --limit 10
```

Run from the project root. The checker validates links, headers and lifecycle rules, canonical edges and frontiers, dependency-pin syntax and revision mismatch, primary-route reachability, and parent cycles.

## Mutation rules

- Use `find` (or `bt allocate PREFIX` in parallel) to avoid ID collisions; a local `find` detects collisions only and never reserves an ID.
- Refresh only the mutated node's `updated`; increment `context_rev` only for a consumer-relevant semantic change. Never update unrelated nodes or the index as bookkeeping.
- Advancing a coordinating parent's `next` after its frontier child is resolved is part of that resolution rather than bookkeeping, so the resolving worker owns that edit; refresh the parent's `updated` and leave its `context_rev` unchanged, because `next` is navigation.
- Change status by moving the unchanged filename between status directories; wikilinks use the basename and stay stable.
- Give each node one primary `Parent [[...]]` or `Area [[IDX-...]]` link; do not add a `Child`/`Parent of` copy to the parent.
- `blocked` only for missing input or external state, with a short `# Blocked` section and a concrete `next` when one exists.
- `resolved` only when the outcome is complete; for a coordinating task verify `Done when`, evidence, and child dispositions first. Remove `next` and keep concise evidence.
- For deprecation or supersession, move to `resolved`, set the sparse `disposition`, record the replacement link, and search remaining backlinks.
- Graph bookkeeping never broadens authorization for code, external systems, or destructive actions.

## Feedback nodes

A consuming project records Braintree friction as an `FBK` node. The `FBK` type is the one feedback marker, so `find nodes -name 'FBK-*.md'` discovers feedback from Markdown alone, with no sidecar, network, or write to the scanned vault.

- Name it `FBK-<n>-<slug>.md` and give it one primary `Parent` or `Area` route into its own vault, like any node.
- Carry the installed Braintree revision as `braintree_revision:` frontmatter, for example `braintree_revision: 0.4.0+g1b58d57`; write `braintree_revision: unknown` when no revision can be determined.
- Read the revision to record with `bt --version` (or `graph-check --version`): an installed skill prints the installer's generated `installed-revision` stamp, `<version>+g<short-sha>`, or `<version>+unknown` when the source revision could not be determined. The declared semantic version stays single-sourced in `pyproject.toml`. Treat the public `<version>` as the compatibility signal and the `+g<short-sha>` as provenance: decide compatibility from the version, and never resolve the source revision against the remote, which the offline record cannot support.
- State the friction in one `# Feedback` section with an `Attempted:`, a `Friction:`, and an `Improvement:` line.

`graph-check` rejects an `FBK` node that omits or malforms `braintree_revision` or lacks the required `# Feedback` content.

Record feedback with the writing half of the mechanism. Run `feedback-record` from the consuming project's vault root and it allocates the next `FBK` id from Markdown, routes the node to the vault's root hub, stamps the revision from the installed record, and writes `nodes/proposed/FBK-<n>-<slug>.md` in one step:

```sh
uv run --project .agents/skills/braintree --frozen feedback-record \
  --attempted '...' --friction '...' --improvement '...'
```

`--nodes` points at the vault's `nodes/` directory when it is not the current directory. `--route 'Area [[IDX-...]]'` overrides the route discovered from `index-map.md`. `--id`, `--summary`, and `--slug` override the allocated id, the summary derived from the friction, and the derived slug. The command reads the installed `installed-revision` record and degrades explicitly to `<version>+unknown` when no record is present, so the node always names the Braintree version in use. The result is a valid, routed `FBK` node that `graph-check` accepts.

To collect feedback from another vault, run the read-only `feedback-scan` command over one or more vault roots:

```sh
uv run --project .agents/skills/braintree --frozen feedback-scan /path/to/vault
```

It reads only `FBK-*.md` frontmatter and prints compact TOON with each node's vault, id, status, Braintree revision, and summary; it prints `feedback: 0 nodes` when there is none. It works on a read-only checkout with no sidecar or network, and never writes to the scanned vault.

Triage each scanned result into this graph: admit a node only when the friction is likely to change a future decision or action, cite the feedback id and revision in the admitted node, and otherwise dispose the result explicitly rather than dropping it silently.

## Node body and status output

Use body headings only for additional information: `# Context` (with `Depends on [[...]] at context_rev N.`), `# Blocked` (`Blocked by`/`Unblocks when`), `# Outcome`, `# Done when`, `# Result`, `# Invariant` for definitions, and `# Feedback` for feedback nodes. A `DEC` node records a settled choice under `# Decision`/`# Rationale`/`# Consequences`. A settled `DEF` or `DEC` is `resolved`; while its invariant or decision is still unsettled it stays `proposed`, so resolving it is the act of settling it. A resolved `DEF` or `DEC` is current knowledge unless its sparse `disposition` says `deprecated` or `superseded`. Index nodes contain pointers, not copied content.

Report graph lists in compact TOON, not JSON or narrative tables, with only the fields needed, e.g. `nodes{id,status,priority,context_rev}: TAS-101,active,P1,3 | DEF-auth,resolved,,7`. State zero results explicitly, and name the resolved node, new status, and advanced frontier in a completion report.
