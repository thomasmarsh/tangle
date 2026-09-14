---
context_rev: 1
priority: P2
updated: 2026-09-14T13:39:55Z
summary: Resolve or dispose the round-eleven Tangle FBK-032 findings.
next: "[[THO-029-pre-dispatch-boundary-evidence]]"
---

Parent [[THO-028-round-eleven-usage-feedback-analysis]].

# Context

Tangle `FBK-032`, recorded at `0.6.0+g169bad5`, was re-verified at HEAD `6664225` in the parent. Findings 2 and 3 are covered mechanisms with brief-template residuals, finding 4 is mostly covered capture behavior with two small residuals, the size half of finding 5 remains owned by [[THO-024-whether-node-files-need-a-bounded-load-band-with]], and batch ID allocation from finding 6 is already resolved by [[TAS-165-batch-node-allocation]].

This round retains three independently consumable outcomes: a contract decision about evidence that justifies pre-dispatch decomposition; a canonical opt-in reconnaissance-reference capability; and a transactional decomposition-authoring workflow. The last outcome folds the small findings 2, 3, and 4 clarity edits into the workflow they make safer rather than admitting mechanical leaves.

# Outcome

Every open round-eleven Braintree finding is decided, implemented, or explicitly disposed, without turning session duration into node identity or duplicating already owned load-band work.

# Done when

- The contract decides whether several independently acceptable outcomes named before dispatch are boundary evidence, and reconciles that answer with both the execution-evidence rule and the rule that a slice is not a split trigger.
- Work nodes can cite shared reconnaissance through one canonical non-pinned relation, and the supported read surface can include that referenced context on demand.
- A transactional authoring surface can allocate and create ordered direct children and advance the parent to its first child without leaving a half-built tree; the parent-advance-only case has a concise supported surface or an explicit disposition.
- The decomposition and brief-authoring guidance names the exact pending-advance check when applicable, prefers `path (Symbol)` for large-module seams, documents `--slug`, and derived capture slugs avoid mid-word clipping or explicitly dispose that residual.
- The size/load-band request remains routed to [[THO-024-whether-node-files-need-a-bounded-load-band-with]] rather than duplicated.
- Every child is resolved or disposed with rationale.
- `make test` passes, and benchmark verification passes if a child changes a benchmark harness or baseline.

# Children

- [[THO-029-pre-dispatch-boundary-evidence]] - Tangle `FBK-032` finding 1.
- [[TAS-190-opt-in-reconnaissance-references]] - new reconnaissance half of finding 5.
- [[TAS-191-transactional-decomposition-authoring]] - finding 6 plus the findings 2, 3, and 4 clarity residuals.
