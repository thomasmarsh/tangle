---
context_rev: 1
status: proposed
updated: 2026-09-14T22:58:32Z
summary: Add a strict Braintree work-packet read surface.
next: Specify the exact routed packet fields and ambiguity behavior.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

One command returns the sole executable frontier node and its minimal execution context, or a structured ambiguity or blocked result.

# Done when

- It follows index, hub, and coordinating `next` routes without a manual parent lookup.
- It reports readiness, pinned dependencies, parent route evidence, files, and verification metadata.
- Tests cover unique, blocked, stale, and ambiguous routes.
