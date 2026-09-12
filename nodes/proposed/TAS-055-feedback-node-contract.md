---
context_rev: 1
priority: P1
updated: 2026-09-12T13:14:11Z
summary: SKILL.md and graph-check define one durable marker and route that make Braintree feedback mechanically discoverable in any vault.
next: Choose the feedback marker and its required content, then encode it in SKILL.md and graph-check.
---

# Context

Parent [[TAS-054-feedback-mechanism]].

# Outcome

`SKILL.md` and `graph-check` agree on one way to mark a node as Braintree
feedback, so a script can find feedback in any vault without reading node bodies
or consulting a sidecar.

# Done when

- The convention fixes a discoverable marker or node type, the required content
  (what was attempted, the friction observed, and the suggested improvement),
  and the primary route that keeps a feedback node reachable.
- `graph-check` validates the convention and reports a clear error for a
  malformed feedback node.
- The convention carries the Braintree revision the feedback is about when one
  is recorded.
- `tests/test_skill.py` pins the contract strings and a validator test exercises
  a valid and an invalid feedback node.
- Discovery works from Markdown alone, with no sidecar, network, or write to the
  scanned vault.
