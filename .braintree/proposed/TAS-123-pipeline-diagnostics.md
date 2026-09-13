---
context_rev: 1
priority: P1
updated: 2026-09-13T18:41:00Z
summary: Attribute benchmark failures to memory writing, retrieval, reading, or action.
next: Define the pipeline failure taxonomy and attribution procedure.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-122-causal-baseline-experiment]] at context_rev 1.

The 540-sample five-arm causal result, including 131 labelled failures, is in
`benchmark/memory-causal-result.json`.

# Outcome

Every benchmark failure is attributable to admission, organization or consolidation, retrieval, stale or conflicting evidence, reading and reasoning, or action, so changes target the demonstrated bottleneck.

# Done when

- The taxonomy has mutually distinguishable labels and an adjudication procedure.
- Retrieval evidence and downstream use are scored separately.
- The initial causal samples are labeled with inter-review agreement or explicit disagreements.
- A diagnostic report ranks bottlenecks by frequency and severity and names which later workstreams are justified.
