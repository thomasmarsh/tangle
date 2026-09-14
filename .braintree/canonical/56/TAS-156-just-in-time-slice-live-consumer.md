---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State that a just-in-time slice under warnings-as-errors includes a live consumer or names it as a mandatory companion.
---

# Context

Parent [[TAS-153-usage-feedback-hardening-round-eight]].

Tangle `FBK-027` at `0.6.0+g3bacaf5`: a model-plus-profile-plus-card slice
decomposed to land before its spawn consumer fails
`cargo clippy --workspace --all-targets -- -D warnings` on an unused trait method
and unread profile fields, so an isolated controller with no live caller is not
independently acceptable. The worker had to wire the spawn path and kernel
dispatch in the same slice, which was larger than the coordinator's example
slice. `rg -in 'dead.?code|live consumer|warnings-as-errors|just-in-time|
independently acceptable' SKILL.md references/` matches nothing.

# Outcome

The decomposition guidance states that in a workspace with warnings-as-errors a
slice that lands a type or trait before its consumer is not independently
acceptable: the slice includes a live consumer, or the node's `next` names the
consumer as a mandatory companion.

# Done when

- The rule is in the `SKILL.md` decomposition guidance and pinned by a contract
  test.
- The rule covers both the live-consumer inclusion and the mandatory-companion
  `next` form.
- `make test` passes.

# Result

`SKILL.md` now states the rule in the boundary guidance of "Admission and the
node boundary", directly after the split/consolidate sentences: "A just-in-time
slice in a warnings-as-errors workspace is not independently acceptable when it
lands a type or trait before its consumer: the slice includes a live consumer, or
the node's `next` names that consumer as a mandatory companion." Both accepted
forms are named, so a slice that lands an unused trait method and unread profile
fields is not independently acceptable unless it wires the caller or its `next`
carries the consumer as the mandatory companion.

`tests/test_skill.py` pins the rule as `_JUST_IN_TIME_LIVE_CONSUMER_RULE` with
`test_just_in_time_slice_includes_or_names_a_live_consumer`, asserting the core
carries all three clauses. The guard rejects the pre-change core: all three
substrings are absent from `HEAD:SKILL.md`, so the test fails when the rule is
removed rather than passing vacuously.

`braintree check` passes (196 nodes) and `make test` passes. `SKILL.md` grew
from 12,779 to 13,020 bytes, inside the `test_core_stays_concise` 16,000-byte
bound. No `context_rev` bump: the added rule is new guidance for future slices
and changes no pinned consumer's assumption, and no node pins this node.
