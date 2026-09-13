---
context_rev: 1
priority: P2
updated: 2026-09-13T19:56:56Z
summary: Measure memory interference and earn a reversible retrieval-suppression policy.
disposition: abandoned
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

# Result

Not executed; abandoned on the round-six diagnostics. The 540-sample causal
result records zero stale-or-conflicting-retrieval labels and attributes the
downstream failures to reading and reasoning rather than to interfering or
superseded guidance, so no interference or forgetting effect is demonstrated on
the development corpus. Per the contract's mechanism rule a suppression policy
cannot be justified, so this workstream is retired rather than run, and it no
longer gates [[TAS-128-confirmatory-memory-evaluation]]. A later growth or
age-gap corpus that shows an interference effect can reopen it as a new node.
