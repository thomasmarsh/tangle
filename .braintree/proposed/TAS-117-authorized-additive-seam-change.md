---
context_rev: 1
priority: P2
updated: 2026-09-13T02:14:00Z
summary: State the bookkeeping when an assigned node's Done-when requires an additive field on a resolved sibling's landed seam.
next: Add the authorized-additive-change paragraph to the coordination reference and pin it.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Tangle `FBK-014` at `0.5.0+g7b95875`, verified in
[[THO-017-round-six-usage-feedback-analysis]]. A slice whose own Done-when
required recording a bank path and content hash in an already-landed
`BatchManifest` that a resolved sibling node owned had no stated rule for
whether that additive, optional field is authorized, who bumps the resolved
owner's `context_rev`, or whether the mechanical struct-literal update in the
owner's test file stays in the consumer's write set. `references/coordination.md`
says a change that "alters a landed seam another node owns ... is escalated
rather than authored" and gives no rule for an authorized additive field;
`additive` matches nothing.

# Outcome

An additive, optional field on a seam a resolved sibling owns, when the
assigned node's Done-when requires it, has stated bookkeeping: the assigned
worker authors it, records the field and affected consumer in its own result,
stays out of the resolved node, and the coordinator decides at integration
whether the owner's `context_rev` needs a bump.

# Done when

- `references/coordination.md` states that an additive, optional field on a seam a resolved sibling owns, when the assigned node's Done-when requires it, is authored by the assigned worker rather than escalated.
- The reference states that the worker records the field and the affected consumer in its own `# Result` and does not edit the resolved node, that mechanical literal updates in the owner's tests stay inside the consumer's write set, and that the coordinator decides at integration whether the owner's `context_rev` needs a bump.
- A contract test in `tests/test_skill.py` pins the stated rule.
- `make test` passes.
