---
context_rev: 1
status: proposed
updated: 2026-09-14T22:58:32Z
summary: Add scoped Braintree verification targets.
next: Map existing source surfaces to focused offline checks.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

Agents can iterate with a documented affected-surface gate while `make test` remains the final repository acceptance gate.

# Done when

- A stable mapping selects lint, type, graph, and focused test checks by named surface.
- The target is faster than the full suite and fails on a deliberate mapped defect.
- Documentation states that it does not replace `make test` before handoff.
