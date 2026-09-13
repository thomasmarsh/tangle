---
context_rev: 1
priority: P2
updated: 2026-09-13T19:48:55Z
summary: Measure memory interference and earn a reversible retrieval-suppression policy.
next: Define the vault-growth and interference experiment.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-123-pipeline-diagnostics]] at context_rev 3.

# Outcome

Vault-growth experiments determine whether resolved, superseded, near-duplicate, and irrelevant memories degrade action quality and whether reversible retrieval suppression improves the trade-off without hiding rare authoritative history.

# Done when

- Fixed tasks run across increasing vault sizes and episode ages with controlled distractors.
- Current-decision recall, stale selection, task success, latency, and token curves are reported.
- Current-view filters, consolidation, and low-utility suppression are compared with no forgetting and age-only decay.
- Any adopted policy is derived, reversible, inspectable, and leaves Git history recoverable.
