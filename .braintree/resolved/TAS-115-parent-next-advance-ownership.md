---
context_rev: 1
priority: P2
updated: 2026-09-13T02:26:37Z
summary: State who advances a coordinating parent's `next` when the resolving worker's write set excludes the parent, and make the stale route detectable.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Tangle `FBK-011` at `0.5.0+g974b178`, reproduced in
[[THO-017-round-six-usage-feedback-analysis]]. A slice resolved its own node
under a handoff whose write set explicitly excluded the coordinating parent, so
after the resolution commit the parent's `next` still named the now-resolved
child; the worker followed the handoff and reported the stale pointer rather
than editing outside its set. `SKILL.md` says "Advancing a coordinating
parent's `next` ... is part of that resolution, so the resolving worker owns
that edit" and gives no rule for a write set that excludes the parent. Probe
`/tmp/bt-ck`: a valid 3-node vault with an unfinished coordinating parent whose
`next: "[[TAS-002-child]]"` names a resolved child passes `braintree check`
(`graph check: passed (3 nodes)`), so the stale route is not flagged either.

# Outcome

The ownership of the parent-next advance is stated for a write set that
excludes the parent, and a stale route — an unfinished coordinating node whose
`next` names an already-resolved node — is visible to a checker or test, so a
resolving worker never has to choose between the handoff and the mutation rule.

# Done when

- `SKILL.md` or `references/coordination.md` states who owns the parent-next advance when the resolving worker's write set excludes the parent: either the handoff names the parent (or its `next`) in the write set, or the coordinator owns the advance and the worker reports the stale pointer as its handoff action.
- `braintree check` reports, or a test asserts detection of, an unfinished coordinating node whose `next` names an already-resolved node.
- Tests cover the stated rule and the detection, and `make test` passes.

# Result

`SKILL.md`'s parent-next mutation rule now states the write-set exception: a
handoff whose write set excludes the parent must name the parent (or its `next`)
in the write set, or the coordinator owns the advance and the worker reports the
stale route as its handoff action. `references/coordination.md` carries the
detail, including the detectable form.

`braintree check` gains the `next-resolved-node` finding: an unfinished
coordinating node whose `next` is a single direct-child link naming an
already-resolved child. It stays silent for an action-sentence `next`, a blocked
node whose `next` is an action, a node without children, and a resolved node
whose `next` is already flagged by `node-resolved-next`.

Evidence: `tests/test_graph_check.py` adds the firing fixture, action-next,
no-children, and blocked-action negatives, and a `next-resolved-node` mutation
in the code-coverage table; `tests/test_skill.py` pins the `SKILL.md` rule and
the coordination stale-route text. A scratch vault falsified the rule: an active
coordinator routed to a resolved child fails with `next-resolved-node`, while
the valid active-coordinator-to-active-child vault passes. `make test` passes
and `braintree check` passes on the live vault, which has no stale routes.
