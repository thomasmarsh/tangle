---
context_rev: 1
updated: 2026-09-12T23:37:21Z
summary: State event-triggered split and consolidation evidence without adding a per-node sizing ritual.
next: Add the compact boundary rule and its contract test.
---

Area [[IDX-001-execution-graph]].

# Context

Depends on [[THO-015-how-should-braintree-correct-task-granularity-wi]] at context_rev 1.

The current skill says agents and nodes are not one-to-one, but it does not positively define node scope as one durable outcome or name the sparse evidence that should trigger reassessment.

# Outcome

Agents can correct over-broad or duplicate node boundaries when execution reveals evidence, while one node may span sessions and one session may advance several nodes without a mandatory sizing pass.

# Done when

- `SKILL.md` defines the node boundary by durable outcome rather than session, agent, commit, or estimated effort.
- The rule names event-triggered evidence for splitting and consolidation and explicitly rejects a mandatory per-node review.
- Existing on-demand commands are identified as advisory support; no checker or command claims semantic authority.
- README and contract tests remain coherent.
- `make test` passes.
