---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Round-eleven findings are decided, implemented, or disposed, and all three children resolved.
---

Parent [[THO-028-round-eleven-usage-feedback-analysis]].

# Context

Hekate `FBK-032`, recorded at `0.6.0+g169bad5`, was re-verified at HEAD `6664225` in the parent. Findings 2 and 3 are covered mechanisms with brief-template residuals, finding 4 is mostly covered capture behavior with two small residuals, the size half of finding 5 remains owned by [[THO-024-whether-node-files-need-a-bounded-load-band-with]], and batch ID allocation from finding 6 is already resolved by [[TAS-165-batch-node-allocation]].

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

- [[THO-029-pre-dispatch-boundary-evidence]] - Hekate `FBK-032` finding 1.
- [[TAS-190-opt-in-reconnaissance-references]] - new reconnaissance half of finding 5.
- [[TAS-191-transactional-decomposition-authoring]] - finding 6 plus the findings 2, 3, and 4 clarity residuals.

# Result

Finding 1 is decided and implemented by [[THO-029-pre-dispatch-boundary-evidence]] in `3a56c13`: `SKILL.md` and `references/authoring.md` admit several authored acceptance outcomes as pre-dispatch boundary evidence, keep duration and budget out of the test, and preserve the negative slice case, with a `tests/test_skill.py` guard and falsification probe. The reconnaissance half of finding 5 is implemented by [[TAS-190-opt-in-reconnaissance-references]] in `0aa2f23`: the non-pinned `Informed by [[THO|DEF|DEC]]` relation in `# Context`, four structural `braintree check` findings, and the one-hop `braintree node references NODE` read surface, with plain `braintree node` unchanged. Finding 6 and the findings 2, 3, and 4 residuals are implemented by [[TAS-191-transactional-decomposition-authoring]] in this commit: `braintree node decompose --parent --plan` validates the whole plan before mutating, rolls back a mid-write failure, and routes the parent to its first child; `braintree node advance` is the parent-advance-only shorthand; the authoring reference documents the plan grammar, the transactional guarantees, and `--slug`; coordination guidance names the exact `--allow-pending-advance PARENT` acceptance command and prefers `path (Symbol)` seams; and derived slugs cut at a whole-word boundary while retaining the cap and fallback.

The size half of finding 5 stays routed to [[THO-024-whether-node-files-need-a-bounded-load-band-with]] and is not duplicated. No child touched a benchmark harness or baseline, so `make test` is the verification: it passes after each commit. The live vault passes `braintree check`.
