---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Use event-triggered boundary evidence to correct node granularity without a per-node sizing ritual.
---

Area [[IDX-001-execution-graph]].

# Question

When agents navigate the graph, how should they notice that one node has grown into multiple durable outcomes or that several nodes are really one outcome, without equating nodes to sessions or imposing a token-heavy sizing review on every task?

# Context

The existing admission and decomposition contracts say agents and nodes are not one-to-one and require durable execution-memory value, but they do not name the evidence that should trigger a boundary reassessment.

# Hypothesis

Use an event-triggered, evidence-based boundary check in the skill and keep tooling advisory and on-demand rather than adding a mandatory per-node sizing command.

# Conclusion

The hypothesis holds. The contract already rejects agent and worktree boundaries as node boundaries, but it states the rule negatively and in sections concerned with admission and parallel work. It never states the positive unit of scope or when new evidence should cause an agent to reconsider it.

Add one compact rule to decomposition: a node owns one durable outcome or decision, not an estimated session, commit, agent assignment, or amount of code. One node may span sessions and one session may advance several frontier nodes. Boundary reassessment is event-triggered rather than mandatory for every node.

The evidence that triggers reassessment is semantic and sparse:

- Split when execution reveals another outcome that can be accepted, verified, consumed, blocked, or resumed independently and that retains durable execution-memory value.
- Consolidate when adjacent nodes share one outcome, completion evidence, and rollback boundary, and neither retains independent future value. Continue the stronger owner and preserve or reconcile backlinks rather than keeping duplicate work.
- Do neither merely because a session ends, another agent takes over, several commits land, or the work is larger or smaller than expected.

Do not add a mandatory sizing command or make `braintree check` fail on scope. The checker can validate graph structure but cannot decide whether two prose outcomes are semantically independent without false authority. Existing bounded commands already support an on-demand investigation: `braintree similar --file PATH` finds likely duplicates, `braintree digest NODE` shows unresolved direct members, and `braintree clusters` can suggest over-broad routes when the optional semantic capability is installed. Use them only after boundary evidence appears.

A future dedicated shape command is justified only if usage evidence shows those separate queries repeatedly cost more than a bounded composed answer. It should remain advisory and expose evidence, never declare an automatic split or merge.

# Decision

Admit [[TAS-104-state-event-triggered-split-and-consolidation-ev]] as one compact documentation-and-contract task for the event-triggered rule. Defer new command work until observed use demonstrates a repeated round-trip problem.
