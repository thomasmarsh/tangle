---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: State who regenerates a resolved node's derived artifacts when a later node's fix invalidates them.
next: State who regenerates a resolved node's derived artifacts when a later node's fix invalidates them.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-022` at `0.6.0+g3bacaf5`: a later slice fixed behavior a resolved
slice owned so the later node's own deliverable would hold, which invalidated
derived artifacts the resolved slice had committed and a test it had written. The
reversal/supersession contract covers reversing an outcome in its own node and
superseding an outcome that moves to a new node, but not a later node changing
behavior a resolved node owns and regenerating that node's derived artifacts.

# Outcome

The reversal/ownership contract states that the node that re-derives a resolved
node's derived artifact performs the change, records the defect, the falsified
artifact, and the regenerated artifact names in its own `# Result`, leaves the
resolved node read-only, and admits a child or sibling when the change is
independently resumable, naming the resolved owner in its `# Context`.

# Done when

- The rule is in `SKILL.md` or `references/dependencies.md` and pinned by a
  contract test.
- Derived-artifact regeneration is reported like a golden regeneration.
- The rule states when the change instead warrants a child or sibling node
  naming the resolved owner.
- `make test` passes.
