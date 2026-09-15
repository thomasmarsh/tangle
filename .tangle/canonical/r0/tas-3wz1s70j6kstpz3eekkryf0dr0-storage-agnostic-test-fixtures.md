---
context_rev: 1
status: proposed
updated: 2026-09-14T22:58:32Z
summary: Abstract storage-specific Tangle test fixtures.
next: Inventory tests that infer node paths or numeric identities.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

Behavioral tests assert node identity and CLI output through shared helpers rather than status-directory or numeric filename assumptions.

# Done when

- Canonical path lookup and deterministic identity injection helpers exist.
- Capture, feedback, decomposition, and installer tests use them.
- A storage-layout change modifies helper fixtures rather than scattered behavior assertions.
