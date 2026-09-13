---
context_rev: 1
priority: P1
updated: 2026-09-13T17:55:00Z
summary: Compare repository-only, raw-history, flat-memory, Braintree, and oracle conditions.
next: Specify the five-arm runner around the frozen corpus.
---

Parent [[TAS-120-agent-memory-evaluation-program]].

# Context

Depends on [[TAS-121-evaluation-foundation]] at context_rev 1.

# Outcome

A matched experiment measures the causal effect of Braintree memory on correct engineering actions relative to repository-only, raw-history, flat-memory, and oracle-evidence conditions.

# Done when

- All arms share frozen fixtures, task prompts, tools, model settings, budgets, and graders.
- Accepted samples pass correctness and telemetry gates before entering cost summaries.
- Each selected case and model has the preregistered repetitions or is reported as missing.
- Paired effects, confidence intervals, tokens, turns, tool calls, latency, and failures are committed with exact reproduction commands.
- Exploratory conclusions are not presented as confirmatory evidence.
