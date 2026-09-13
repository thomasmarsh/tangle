---
context_rev: 1
priority: P2
updated: 2026-09-13T19:48:55Z
summary: Evaluate uncertainty, source provenance, unresolved conflict, and memory poisoning.
next: Define conflict, provenance, and authority-threat cases.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-123-pipeline-diagnostics]] at context_rev 3.

# Outcome

Braintree preserves uncertainty and source authority well enough to avoid overconfident action, resolve or retain genuine conflicts, and prevent persistent memory from granting instructions or permissions.

# Done when

- Cases distinguish observations, inferences, decisions, user instructions, trusted tests, and untrusted external content.
- Correct actions include clarification, calibrated abstention, preserving alternatives, and refusing authority escalation.
- Write, retrieval, activation, and harmful-action rates are measured for direct and laundered memory injection.
- Sparse provenance or temporal fields are adopted only when they improve held-out correctness over existing Markdown and Git evidence.
