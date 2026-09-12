---
context_rev: 1
priority: P1
updated: 2026-09-12T13:25:14Z
summary: A consuming project records Braintree struggles and improvements as routed nodes that this project can mechanically discover and triage.
next: Start [[TAS-056-feedback-recording-path]].
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
