---
context_rev: 1
status: resolved
updated: 2026-09-14T23:14:02Z
summary: Add a strict Tangle work-packet read surface.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

One command returns the sole executable frontier node and its minimal execution context, or a structured ambiguity or blocked result.

# Done when

- It follows index, hub, and coordinating `next` routes without a manual parent lookup.
- It reports readiness, pinned dependencies, parent route evidence, files, and verification metadata.
- Tests cover unique, blocked, stale, and ambiguous routes.

# Result

Specified the `tangle packet` read contract. It resolves each root hub from
`index-map.md` and follows a coordinating node's single wikilink `next` until
it reaches an unfinished node with an action `next`. A routed node is
executable only when it is `active` or `proposed`, has no blocked or stale
context edge, and every traversed route is a direct `Parent` link. A blocked
node ends that route as blocked rather than falling through to another
candidate.

The unique success packet is TOON with `result: ready`, the node `id`, `name`,
`path`, `status`, `summary`, and action `next`; a `route` table with each
parent-to-child hop; a `dependencies` table with relation, target, pinned
revision, current revision, target status, and stale verdict; plus `files`
and `verification` metadata. `files` initially contains the node Markdown
path; `verification` names `tangle check` and `make test` as the required
final gates.

No route is selected heuristically. Zero executable routes returns
`result: blocked` with one row per terminal blocked/stale route. More than one
distinct executable node returns `result: ambiguous` with one candidate row
per node and exits 1. A malformed route, missing target, cycle, or a `next`
link that is not a direct child returns `result: invalid` with route evidence
and exits 1; command-line misuse exits 2. `ready` exits 0. Candidate and route
rows sort by stable node identity, making the response deterministic.

Completed the implementation slice. `index.packet` derives the strict packet
from `index-map.md` root hubs and each coordinating node's single `next` route;
`src/tangle/packet.py` renders it as the `tangle packet` verb, registered
in `main.py` and documented by its own bounded verb help. `tests/test_packet.py`
covers unique, blocked, stale, and ambiguous routes plus malformed, missing,
not-a-child, cycle, no-hub, argument, and absent-vault failures, and
`tests/test_skill.py` and `tests/test_orphan_warning.py` include the verb in
their public-verb and direct-answer checks. On the shipped vault the verb
correctly reports `ambiguous` for the two live executable routes, TAS-203 and
this node, rather than guessing.

`ruff`, `mypy`, and the packet tests pass. `make test` reaches 806 passing
tests and 2 pre-existing failures unrelated to this node: `test_memory_authority`
(the frozen authority-artifact re-derivation) and
`test_frontier_matches_markdown_on_live_vault`, whose status-directory test
recipe does not yet discover canonical nodes, owned by
[[tas-3wz1s70j6kstpz3eekkryf0dr0-storage-agnostic-test-fixtures]].
