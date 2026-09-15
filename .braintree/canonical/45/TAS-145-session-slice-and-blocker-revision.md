---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State the session-slice rule and whether clearing a blocker is a semantic context_rev bump.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Hekate `FBK-024` at `0.6.0+g3bacaf5`: a frontier node's `# Done when` spanned
several sessions, and `SKILL.md` says one node may span sessions but never sizes a
session to a coherent slice, so read literally the rules push either toward no
progress or toward silently attempting every deliverable. Separately, `SKILL.md`
says never bump `context_rev` for a status move, leaving unclear whether a
`blocked`->`proposed` move that flips whether downstream increments may start is
a status move or a semantic change; the worker had to choose and recorded a bump
to `3`.

# Outcome

`SKILL.md` states that a frontier node whose `# Done when` cannot be met in one
session is advanced by the smallest coherent slice, with the remaining scope and
evidence recorded in the body and the node left `proposed` or `active` with a
`next` naming the first remaining action, and that unblocking is not completing;
it also states whether clearing a blocker bumps `context_rev`.

# Done when

- The session-slice rule is in the status/next section and pinned by a contract
  test.
- The blocked-to-proposed `context_rev` question is answered explicitly.
- The rule keeps one node/one outcome without adding a sizing ritual.
- `make test` passes.

# Result

`SKILL.md` `## Status, next, and roll-up` gains one paragraph after the
blocked-versus-proposed paragraph: a frontier node whose `# Done when` "cannot be
met in one session is advanced by the smallest coherent slice", the completed
slice, the remaining scope, and its evidence are recorded in the body, `next` is
"set ... to the first remaining action", and the node stays `proposed` or
`active`. It states "Unblocking is not completing": clearing a blocker returns
the node to `proposed`, "never to `resolved`". The paragraph closes the sizing
question without a ritual — "A slice is a unit of execution, not a split trigger
or a sizing ritual" — so the node keeps its one outcome and its boundary and no
session boundary, agent change, or commit count sizes a session or reassesses the
node.

The `context_rev` answer is explicit and negative on both surfaces.
`SKILL.md`'s `context_rev` bullet now states: "Clearing a blocker is exactly that
status move with a `next` change, so it never bumps `context_rev`: a consumer
detects readiness from the status directory, and a semantic change made in the
same edit still bumps it." `references/dependencies.md` `## Pins, gates, and
staleness` states the same for the revision reference an agent loads before
bumping or gating: "Clearing a blocker is the same status move with a `next`
change, so it never bumps `context_rev` either: a consumer reads readiness from
the status directory, and its gate clears when the target resolves, not when the
node returns to `proposed`." The reported round-seven bump to `3` was therefore
not owed by the unblock; a blocked target is not `resolved`, so its consumer
keeps its gate and no pinned consumer reads a revision, and only a semantic
change made in the same edit bumps it. This closes Hekate `FBK-024`.

`tests/test_skill.py` pins both with `_SESSION_SLICE_RULE` (the smallest-coherent-
slice advance, the body evidence, the first-remaining-action `next`, the
`proposed`/`active` status, "Unblocking is not completing", never `resolved`, and
the no-sizing-ritual clause) and `_BLOCKER_CLEARANCE_REVISION_RULE` (the
status-move framing in `SKILL.md`, the status-directory readiness answer, the
same-edit semantic clause, and the reference's gate-clears-on-resolution clause),
asserted by `test_session_slice_rule_is_stated` and
`test_clearing_a_blocker_is_not_a_context_rev_bump`. Falsification probes
`_SESSION_SLICE_PROBE_SESSION_SPAN_ONLY` (the durable-outcome boundary sentence,
which already names spanning sessions) and
`_BLOCKER_CLEARANCE_PROBE_STATUS_MOVE_ONLY` (the pre-change status-move bullet
plus the pre-change resolution sentence) run through the same `_assert_contains`
guard and require `AssertionError` in
`test_session_slice_guard_rejects_the_session_span_boundary_alone` and
`test_blocker_clearance_guard_rejects_the_status_move_rule_alone`. Measured
against `HEAD`, the slice rule is missing all 7 clause groups from both the probe
and `HEAD:SKILL.md`, and the blocker rule is missing all 5 clause groups from
both the probe and the pre-change `SKILL.md` + `references/dependencies.md`, so
neither guard passes vacuously.

`SKILL.md` remains inside the concise-core bound after the two additions:
15,375 bytes against `_CORE_SIZE_BOUND = 16_000`.

Evidence: `uv run pytest -q tests/test_skill.py` -> 92 passed; `braintree check`
-> `graph check: passed (197 nodes)`; `make test` -> 686 passed, 3 skipped, 79
deselected. No context-bearing dependency is
pinned to this node and no node pins it, so no consumer reconciliation was needed
and `context_rev` stays at `1`. The parent [[TAS-137-usage-feedback-hardening-round-seven]]
names this node in its write set, so its `next` advanced to
[[TAS-146-summary-truncation-integrity]] in this change.
