---
context_rev: 1
priority: P1
updated: 2026-09-12T12:40:14Z
summary: Resolve the external usage-feedback findings across allocation, backlinks, pins, and lifecycle guidance without regressing Markdown authority.
next: [[TAS-045-id-reservation-reconciliation]]
---

# Context

Parent [[THO-008-external-usage-feedback-analysis]].

The source friction is the Tangle vault's `IDX-002-braintree-feedback.md` and
`THO-003-braintree-usage-postmortem.md`, analyzed for this vault in the parent.

# Outcome

The three confirmed `bt` defects and five contract gaps are fixed or explicitly
disposed, with regression tests that reproduce the reported behavior first.

# Done when

- `bt allocate` never returns an identity that already exists on disk, and
  `id_sequences` is reconciled from Markdown.
- Reservations are auditable or reclaimable.
- `bt backlinks` resolves a node name and distinguishes a node with no edges
  from an unknown node.
- `graph-check` and `SKILL.md` agree on context-pin line termination, the `next`
  grammar, `blocked` versus a proposed dependency, requested plans, and the
  status-directory contract.
- `make test` passes with new regression tests for each confirmed defect.
- Every child is resolved or disposed with rationale.
