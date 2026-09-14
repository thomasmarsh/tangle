---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: State event-triggered split and consolidation evidence without adding a per-node sizing ritual.
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

# Result

Added one compact rule to `SKILL.md` under `## Decomposition and roll-up`: a node owns one durable outcome or decision, not an estimated session, commit, agent assignment, or amount of code; one node may span sessions and one session may advance several frontier nodes; and boundary reassessment is event-triggered evidence rather than a mandatory per-node sizing pass. The rule states the sparse split evidence (another outcome that can be accepted, verified, consumed, blocked, or resumed independently and that retains durable execution-memory value) and the consolidation evidence (adjacent nodes sharing one outcome, completion evidence, and rollback boundary with no independent future value, continuing the stronger owner and preserving or reconciling backlinks), and it rejects splitting or consolidating merely because a session ended, an agent changed, several commits landed, or the work is larger or smaller than expected. It names `braintree similar --file PATH`, `braintree digest NODE`, and `braintree clusters` (optional semantic capability) as advisory support only, used after boundary evidence appears, and states that no checker or command claims semantic authority over scope because `braintree check` validates graph structure only.

`README.md` records the same durable-outcome boundary and event-triggered reassessment in its decomposition paragraph. `tests/test_skill.py` adds `test_skill_durable_outcome_boundary_contract` and `test_readme_durable_outcome_boundary_contract` over the required rule phrases plus the absence of a mandatory sizing command, leaving the existing literal grammar intact.

Evidence: `braintree check nodes` passes; `uv run pytest tests/test_skill.py -q` reports 28 passed; `make test` passes. Dependency: THO-015 is resolved at `context_rev 1`, matching the pin.
