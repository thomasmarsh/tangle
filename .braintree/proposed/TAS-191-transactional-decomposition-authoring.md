---
context_rev: 1
updated: 2026-09-14T13:39:48Z
summary: Make ordered decomposition atomic and its briefs immediately executable.
next: Specify the plan input and all-or-nothing mutation contract.
---

Parent [[TAS-189-usage-feedback-hardening-round-eleven]].

# Context

Tangle `FBK-032` finding 6 reports that deliberate decomposition requires one capture invocation per child followed by a second pass to advance each parent. [[TAS-165-batch-node-allocation]] removed the ID-reservation half but did not create routed children or update the parent. A failure between those writes can leave a half-built tree.

This node also owns the small authoring residuals from findings 2, 3, and 4 because they make the same decomposition and dispatch workflow safer but do not retain independent execution-memory value: acceptance should name `braintree check --allow-pending-advance PARENT` when the parent is outside the write set; a large-module seam should prefer `path (Symbol)`; the authoring reference should expose `--slug`; and the derived capture slug should not end in a word fragment.

# Outcome

A coordinator can author an ordered set of direct children and route the parent to the first child in one all-or-nothing operation, while generated briefs and capture names remain precise enough to execute without avoidable correction passes.

# Done when

- One supported command accepts a declared parent and a reviewable ordered-child plan, validates every child before mutation, reserves all required IDs coherently, writes every child with its canonical `Parent` route and executable `next`, and advances the parent to the first child atomically from the caller perspective.
- Failure before commit leaves no authored child or parent edit; reservation behavior is explicit and consistent with the burn-on-discard allocator contract.
- The command never writes reciprocal child lists, silently rewrites parent acceptance, or infers semantic node boundaries from the plan.
- The input format, dry-run or preview behavior, collision handling, status defaults, output, and recovery contract are documented and tested.
- The parent-advance-only case has a concise supported command or is explicitly disposed with rationale after comparing it with direct Markdown editing.
- Coordination brief guidance requires the exact `--allow-pending-advance PARENT` acceptance command when a resolving worker cannot edit the parent, and prefers `path (Symbol)` citations for seams in large modules.
- The authoring reference documents the existing `--slug` override.
- Derived slugs cut at a whole-word boundary when possible, retain the existing length and fallback guarantees, and have capture tests for long single-word and multi-word summaries; if this is rejected, the result records why the explicit override is sufficient.
- `make test` passes.
