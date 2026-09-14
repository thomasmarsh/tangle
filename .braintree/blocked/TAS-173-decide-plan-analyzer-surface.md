---
context_rev: 1
updated: 2026-09-14T02:16:26Z
summary: Decide whether pilot evidence justifies a dry-run planning-document analyzer.
next: Answer whether and how Braintree should analyze source plans.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-171-pilot-incremental-plan-intake]].

The analyzer is conditional. Manual pilot evidence must show repeated classification, owner-discovery, contradiction, or citation cost before a command is admitted.

# Outcome

A settled choice either defines a bounded read-only analyzer or disposes the product branch with evidence.

# Done when

- The decision names the repeated pilot cost the analyzer would remove.
- It decides deterministic, optional-model, or hybrid analysis and states the offline and degradation behavior.
- It defines inputs, source-span citations, output schema, uncertainty, existing-owner search, and graph-currentness behavior.
- It states whether any reviewed follow-up command may mutate Markdown; automatic node creation and inferred authoritative boundaries remain forbidden unless separately decided.
- It defines held-out cases for duplicated owners, operative definitions, historical rationale, speculative work, stale checklists, and contradictions.
- If the command is not justified, [[TAS-174-build-dry-run-plan-analyzer]] is explicitly disposed.

# Blocked

Blocked by: a project-owner product decision that must be made with the manual-pilot evidence.

Questions for the project owner:

1. If repeated intake cost is demonstrated, should Braintree add a dedicated analyzer command?
2. Must analysis be entirely deterministic and offline, or may an optional LLM or semantic provider contribute advisory classifications?
3. Should output be compact TOON only, a reviewable Markdown mapping, a patch proposal, or more than one surface?
4. May a separately confirmed operation ever create nodes, or must the tool remain permanently read-only?
5. What latency, token, dependency, and privacy constraints apply to reading very large plans?
6. Which classification errors are tolerable, and which must cause the tool to abstain?

Unblocks when: pilot evidence exists and the owner answers these product-boundary questions.
