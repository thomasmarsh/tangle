---
context_rev: 1
priority: P0
updated: 2026-09-14T18:55:20Z
summary: Deliver opt-in parallel graph mutation and reconciliation.
next: "[[DEF-003-opt-in-change-intake-protocol-v1]]"
---

Area [[IDX-001-execution-graph]].

# Context

The implementation plan is grounded in `research/parallel-graph-mutation-and-reconciliation.md`. Its governing constraint is progressive disclosure: direct Markdown remains the default for a single writer; coordination machinery is loaded and paid for only when concurrency risk requires it.

The first required deployment is several clients contributing graph mutations from one working directory without concurrently editing canonical node files. The second is independent Git worktrees whose contributions must be reconsidered against the current target during rebase or integration. Cross-host transport, semantic assistance, and retention policy are follow-on capabilities.

# Outcome

Braintree accepts asynchronous graph contributions through an opt-in, immutable intake and reconciliation path that first supports one shared working directory, then Git worktrees, without expanding the compliance burden of ordinary direct editing.

# Done when

- A versioned contract defines the escalation triggers, proposal identity and encoding, supported operations, preconditions, repository-effect boundary, dispositions, receipts, and compatibility behavior.
- Same-directory clients can submit immutable graph proposals concurrently, inspect the pending set, reconcile overlap deterministically, require explicit decisions only for ambiguity, and serialize accepted canonical mutations with recovery evidence.
- Worktree contributions can be normalized, checked against a moved target, reconciled during rebase or integration, and accepted only with their bound repository effect.
- The skill retains only a compact routing rule; conditional references and command help contain the detailed protocol.
- Ordinary single-writer editing, existing assigned-write-set coordination, and current `braintree reconcile` callers remain compatible unless they opt into the new path.
- Each phase has adversarial multi-client coverage, the relevant fast and benchmark gates pass, and deferred cross-host or advanced semantic work remains explicitly scoped rather than leaking into the initial releases.
