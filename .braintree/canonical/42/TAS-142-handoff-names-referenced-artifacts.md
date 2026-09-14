---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Require a handoff to name the concrete path of an artifact it orders reused or introduced.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-020` at `0.6.0+g3bacaf5`: a handoff instructed a worker to reuse "the
existing experiment-spec and seed-bank formats from Increment 5" when no
checked-in input artifact or format existed; the seed bank was concrete but the
only specification surface was a recorded output field, so the worker had to
invent the artifact and its shape for a downstream slice to consume. The
coordination reference has no rule that a handoff names the concrete artifact it
orders reused or introduced.

# Outcome

The coordination reference states that a handoff which orders reuse of an
existing artifact names its concrete path (or the node that owns it), that a
worker must not invent a referenced artifact that does not exist, and that when
the artifact is new the handoff or plan declares its path and format.

# Done when

- The rule is in `references/coordination.md` and pinned by a contract test.
- The rule covers both "reuse an existing artifact" and "introduce a new
  artifact" handoffs.
- The worker's stop-and-ask path is explicit.
- `make test` passes.

# Result

`references/coordination.md`'s **Worker handoff** section now carries the
artifact-naming rule the `FBK-020` probe lacked: a handoff that orders reuse of
an existing artifact names its concrete path — or the node that owns it — so the
worker reads an input instead of inferring a shape; a worker that cannot resolve
an ordered artifact to a path or an owning node does not invent it and stops and
asks the coordinator, because a fabricated artifact silently becomes the
interface a downstream slice consumes; and when the ordered artifact is new, the
handoff or the node's plan declares its path and format before the worker authors
it. One paragraph covers both handoff kinds on the surface a worker reads before
editing, and the stop-and-ask path is the explicit escalation to the coordinator
rather than a silent authoring decision.

Tests: `tests/test_skill.py` adds `test_handoff_names_a_referenced_artifact`,
which pins `_HANDOFF_ARTIFACT_NAMING_RULE` — five literal strings spanning the
reuse, no-invention, stop-and-ask, and new-artifact clauses — against
`references/coordination.md`, plus
`test_artifact_naming_guard_rejects_the_handoff_protocol_alone`, whose probe
`_HANDOFF_ARTIFACT_NAMING_PROBE` is the pre-change handoff paragraph: it names
the assigned write set and the changed, created, and moved paths a worker
reports but carries none of the rule strings, so the guard fails when it stops
detecting the rule rather than when the paragraph merely reflows.

`SKILL.md` is unchanged: the rule rides the already-routed **coordination**
topic, so the core stays inside its size bound.

`braintree check` passes (196 nodes) and `make test` passes.
