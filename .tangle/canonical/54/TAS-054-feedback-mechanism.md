---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: A consuming project records Tangle struggles and improvements as routed nodes that this project can mechanically discover and triage.
---

# Context

Area [[IDX-001-execution-graph]].

# Outcome

The installed skill defines one feedback convention, gives a consuming project a
low-friction way to record a struggle or suggested improvement under it, and
lets this project scan another vault's `nodes/` to collect that feedback into
its own self-improvement plan.

# Done when

- The convention names the feedback marker or type, the required content, and
  the route that keeps feedback reachable in a consuming project.
- A consuming project records feedback through a documented step that yields a
  valid node under the convention.
- A maintainer scans an external vault's `nodes/` and receives the feedback as
  a compact, bounded result without hand-searching every node.
- Feedback that passes admission becomes admitted work in this graph; feedback
  that does not is explicitly disposed.
- `SKILL.md` and `graph-check` document and enforce the convention, with tests.
- Every child is resolved or disposed with rationale.

# Result

The feedback mechanism is complete. `FBK` is the one feedback marker, carrying
a `tangle_revision` field and an
`Attempted:`/`Friction:`/`Improvement:` `# Feedback` section that `graph-check`
enforces and `SKILL.md` documents ([[TAS-055-feedback-node-contract]]). A
consuming project records feedback in one step with the `feedback-record`
writer ([[TAS-056-feedback-recording-path]]), and a maintainer collects it from
external vaults with the read-only `feedback-scan` collector and the documented
admission/disposal triage ([[TAS-057-cross-project-feedback-collection]]).

Evidence:

- [[TAS-055-feedback-node-contract]], [[TAS-056-feedback-recording-path]], and
  [[TAS-057-cross-project-feedback-collection]] are resolved with tests.
- `SKILL.md` documents the convention, the recording step, the scan, and the
  triage; `graph-check` enforces the convention.
- `make test` passes.
