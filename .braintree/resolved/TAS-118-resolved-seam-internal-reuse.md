---
context_rev: 1
priority: P2
updated: 2026-09-13T02:35:53Z
summary: State the rule for internal, non-behavioral reuse of a resolved sibling's seam by widening visibility instead of duplicating it.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Tangle `FBK-015` finding 1 at `0.6.0+g4c6cafb`, verified in
[[THO-017-round-six-usage-feedback-analysis]]. A slice needed the metric-key
mapping and interval arithmetic a resolved sibling owned and chose reuse by
widening private items to `pub(crate)` rather than duplicating the seam. Every
option was an unstated judgment call with different bookkeeping: widen
visibility, duplicate the seam (risking two drifting spellings), or escalate a
decision that changes no observable behavior. `references/coordination.md`
escalates a change that "alters a landed seam another node owns" and asks the
worker to record any authored primitive, but `pub(crate)`, `visibility`, and
`reuse` match nothing in `SKILL.md` or `references/`, so it is unstated whether
a non-public visibility widening counts as altering a landed seam, who owns the
resolved node's `context_rev`, or whether the owner node must be edited.

# Outcome

An internal, non-behavioral reuse change in a resolved node's module —
widening an item to `pub(crate)`, or adding a `pub(crate)` helper an existing
private item delegates to — has a stated rule, so a worker can reuse one
spelling of a seam without escalating a decision that changes no observable
behavior.

# Done when

- `references/coordination.md` states that an internal, non-behavioral reuse change in a resolved node's module is authored by the assigned worker without escalation when it changes no artifact byte, no public API, and no behavior.
- The reference states that the worker records the widened items, the reason, and the resolved owner in its own `# Result`, does not edit the resolved node, and does not bump its `context_rev` because no consumer assumption changes, and it states the boundary sentence: visibility and `pub(crate)` factoring are not seam alterations unless a consumer outside the crate or an artifact shape changes.
- The reference states that duplicating the seam inside the new module is preferred over escalating when reuse would otherwise copy the spelling.
- A contract test in `tests/test_skill.py` pins the stated rule.
- `make test` passes.

# Result

`references/coordination.md` states the internal-reuse rule as a compact
paragraph immediately after the additive-field bullet: an internal,
non-behavioral reuse change in a resolved node's module — widening an item to
`pub(crate)`, or adding a `pub(crate)` helper an existing private item delegates
to — is authored by the assigned worker without escalation when it changes no
artifact byte, no public API, and no behavior. The worker records the widened
items, the reason (one spelling instead of two), and the resolved owner in its
own `# Result`; it does not edit the resolved node and does not bump its
`context_rev`, because no consumer assumption changes. The paragraph states the
boundary — visibility and `pub(crate)` factoring are not seam alterations unless
a consumer outside the crate or an artifact shape changes — and states that
duplicating the seam inside the new module is preferred over escalating when
reuse would otherwise copy the spelling. No artifact byte, public API, or
behavior changed, and no consumer assumption changed, so this node stays
`context_rev` 1.

Evidence: `tests/test_skill.py` pins the rule with `_INTERNAL_SEAM_REUSE_RULE`
in `test_internal_reuse_of_a_resolved_seam_is_authored_by_the_consumer`;
removing the paragraph from `references/coordination.md` fails that test.
`make test` and `braintree check` pass.
