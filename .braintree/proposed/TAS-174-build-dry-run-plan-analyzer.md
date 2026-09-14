---
context_rev: 1
updated: 2026-09-14T02:16:27Z
summary: Build a reviewable dry-run planning-document analyzer if justified.
next: Implement and evaluate the decided read-only source-plan analysis surface.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-173-decide-plan-analyzer-surface]].

This node is resolved only if the analyzer is admitted; otherwise it is disposed under the coordinating task.

# Outcome

A bounded analyzer turns a large plan into a cited review proposal without mutating the graph or granting inferred structure authority.

# Done when

- The surface classifies cited sections as update-existing, candidate outcome, decision or definition, completed or historical, narrative-only, deferred speculation, stale or contradictory, or uncertain.
- Existing-owner candidates include the evidence and selection reason rather than a bare similarity score.
- Exact source spans and source versions let a reviewer verify every recommendation.
- The analyzer reports uncertainty and competing mappings instead of forcing one boundary.
- Headings, chunks, checkboxes, and generated entities never become nodes automatically.
- Tests cover duplicates, contradictions, stale status, rewritten headings, large files, missing optional providers, and zero-result cases.
- An evaluation compares the analyzer with the manual protocol on classification quality, review cost, tokens, latency, and downstream action correctness.
