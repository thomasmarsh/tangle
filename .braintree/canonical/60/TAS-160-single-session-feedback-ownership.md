---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State who owns the single session FBK node so workers do not each create one.
---

# Context

Parent [[TAS-153-usage-feedback-hardening-round-eight]].

Hekate `FBK-029` finding 3 at `0.6.0+g3bacaf5`: two workers independently created
Hekate `FBK-027` and `FBK-028` before the coordinator recorded Hekate `FBK-029`,
so one orchestration session produced three feedback nodes against the
consuming project's "one `FBK` node per session" rule. Neither `SKILL.md` nor
`references/authoring.md` states who owns the session `FBK` or whether a worker
may create one.

# Outcome

The authoring or coordination reference states that the coordinator owns the
single session `FBK` node and that a worker reports friction in its run report
instead of creating a node unless the coordinator explicitly grants it; or, as
the documented alternative, worker `FBK` nodes are permitted with the
one-per-session rule scoped explicitly to the orchestration session.

# Done when

- The ownership rule is stated in `references/authoring.md` or
  `references/coordination.md` and pinned by a contract test.
- The rule names the coordinator's ownership and the worker's report path.
- `make test` passes.

# Result

Took the primary branch of the outcome, not the documented alternative.
`references/authoring.md`'s "Feedback nodes" section states the rule directly
after its introduction: "One session records one session `FBK` node, and the
coordinator owns it". A worker that hits friction "reports it in its run report —
the attempted action, the friction, and the improvement — instead of creating a
node", and the coordinator decides whether that report becomes the session `FBK`
node, folds into one already recorded, or is disposed; "A worker creates an `FBK`
node only when the coordinator explicitly grants it". The one-per-session rule is
scoped explicitly to the orchestration session, not to each worker run, so the
two workers that produced Hekate `FBK-027` and `FBK-028` before the coordinator
recorded `FBK-029` owe one report, not three nodes.

`tests/test_skill.py` pins the rule as `_SINGLE_SESSION_FEEDBACK_OWNERSHIP_RULE`
(the ownership sentence, the run-report path with its attempted/friction/
improvement content, the no-node-unless-granted clause, the coordinator's
admit-fold-dispose decision, and the orchestration-session scoping) with the
source-named `test_single_session_feedback_node_is_coordinator_owned`. The
falsification probe `_SINGLE_SESSION_FEEDBACK_OWNERSHIP_INTRO_ONLY` feeds the
feedback-node introduction — which carries the `FBK` token and its discovery
command but names no owner — through the same `_assert_contains` guard and
requires `AssertionError` in
`test_single_session_feedback_ownership_guard_rejects_the_intro_alone`, so the
test fails when the guard stops detecting the rule rather than passing vacuously.
The widened rule reports all eight clause groups missing against both the probe
and `HEAD:references/authoring.md`, so neither passes.

`SKILL.md` and `references/coordination.md` are unchanged: the rule is
conditional feedback-recording detail, the core already routes that workflow to
`references/authoring.md`, and the `test_core_stays_concise` bound keeps the core
narrow, so a second statement would duplicate the spelling rather than add a
contract.

Evidence: `uv run pytest -q tests/test_skill.py` -> 71 passed; `braintree check`
-> `graph check: passed (196 nodes)`; `make test` -> 655 passed, 3 skipped, 79
deselected. No context-bearing dependency is pinned to this node and no node pins
it, so no consumer reconciliation was needed and `context_rev` stays at `1`. The
parent [[TAS-153-usage-feedback-hardening-round-eight]] named this node in its
write set; it is the last child, so that parent was rolled up in this change
rather than re-routed.
