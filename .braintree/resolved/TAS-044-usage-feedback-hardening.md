---
context_rev: 1
priority: P1
updated: 2026-09-12T12:50:07Z
summary: All five usage-feedback hardening children resolved with regression tests and no regression to Markdown authority.
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

# Result

All five children resolved: [[TAS-045-id-reservation-reconciliation]],
[[TAS-046-backlinks-name-resolution]],
[[TAS-047-context-pin-line-contract]],
[[TAS-048-frontier-lifecycle-guidance]], and
[[TAS-049-output-and-directory-clarity]].

Evidence:

- Allocation seeds from Markdown maxima, skips identities already on disk, and
  `bt status` reports reservations (TAS-045).
- `bt backlinks` resolves a full name or bare ID and errors on an unknown node
  while keeping the zero result for a real edgeless node (TAS-046).
- `graph-check` names trailing text after a context pin and `SKILL.md` states
  the line-termination rule (TAS-047).
- `SKILL.md` defines the direct-child test and `next` forms, contrasts blocked
  with a proposed sibling, and permits a requested proposed plan (TAS-048).
- Status directories appear on demand and `bt stale` names stale pins in its
  zero result (TAS-049).
- `make test` passes with new regression tests for every confirmed defect.
