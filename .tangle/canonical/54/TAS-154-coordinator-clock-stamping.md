---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State that a coordinator stamps the host clock at handoff so it does not create a carried timestamp clamp.
---

# Context

Parent [[TAS-153-usage-feedback-hardening-round-eight]].

Hekate `FBK-026` finding 4 at `0.6.0+g3bacaf5`: a coordinator stamped a parent
`updated` ahead of the host clock on an early handoff; the worker clamp
`max(now, previous updated)` preserved that future time, so every later edit in
the session looked stale against the children's real times. `SKILL.md` stated
the clamp and that "a coordinator stamps the real UTC time at handoff", but not
that the stamped value must be the host clock rather than a rounded or estimated
one.

# Outcome

`SKILL.md` states that a coordinator stamps the host clock at handoff rather than
a rounded or estimated value, so it never creates a future `updated` the session
must carry.

# Done when

- `SKILL.md` states the host-clock stamping rule.
- A contract test pins the rule.
- `make test` passes.

# Result

`SKILL.md`'s `updated`/`context_rev` bullet now reads: "A coordinator stamps the
host clock at handoff — the real host clock time, not a rounded or estimated
value — so it hands no worker a future `updated` to clamp; a worker refreshing
an inherited `updated` ahead of the host clock uses `max(now, previous updated)`
and notes the clamp rather than moving it backwards." This repins the rule to
the host clock explicitly and names the carried-clamp failure it prevents.

`tests/test_skill.py` pins the new literal: `_COORDINATOR_HOST_CLOCK_STAMP_RULE`
("A coordinator stamps the host clock at handoff", "the real host clock time,
not a rounded or estimated value") is asserted by the new
`test_coordinator_stamps_the_host_clock_at_handoff`, and `_UPDATED_CLAMP_RULE`
drops the retired "real UTC time at handoff" literal while keeping the worker
clamp pin. `references/coordination.md` does not restate the stamp, so it is
unchanged.

Evidence: `uv run pytest -q tests/test_skill.py` -> 63 passed; `make test` ->
all green; `tangle check` -> graph check passed (196 nodes). `SKILL.md` grows
to 12,779 bytes, within the 16,000-byte `test_core_stays_concise` bound.

No context-bearing dependency was pinned to this node, so no consumer
reconciliation was required and `context_rev` stays at `1`.
