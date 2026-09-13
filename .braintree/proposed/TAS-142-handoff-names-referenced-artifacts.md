---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: Require a handoff that orders reuse of an artifact to name its concrete path or the worker stops.
next: Require a handoff that orders reuse of an artifact to name its concrete path or the worker stops.
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
