---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: State the bookkeeping when an assigned node's Done-when requires an additive field on a resolved sibling's landed seam.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Hekate `FBK-014` at `0.5.0+g7b95875`, verified in
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

# Result

`references/coordination.md` now states the additive-field exception in the
parallel-worktree contract: an additive, optional, behavior-preserving field on
a seam a resolved sibling owns, when the assigned node's `Done when` requires
it, is authored by the assigned worker rather than escalated. It is scoped as
the exception to the preceding sentence that a change altering a landed seam
another node owns is escalated rather than authored: it covers the field, not a
behavioral or public-schema change. The worker records the field and the
affected consumer in its own `# Result` and does not edit the resolved node;
mechanical literal updates in the owner's tests stay inside the consumer's write
set; and the coordinator decides at integration whether the owner's `context_rev`
needs a bump.

Evidence: `tests/test_skill.py` pins the rule with
`_ADDITIVE_RESOLVED_SEAM_FIELD_RULE` in
`test_additive_field_on_a_resolved_seam_is_authored_by_the_consumer`. It passes,
and removing the seven-line reference bullet falsifies it:
`uv run pytest tests/test_skill.py -q -k additive` then fails with
`missing contract text: ["an additive, optional, behavior-preserving field ..."]`.
Restoring the bullet passes again. `make test` and `tangle check` pass.

The node carried a stale lease from the cut-off writer `worker` whose recorded
base hash did not match the current content: `tangle claim
TAS-117-authorized-additive-seam-change worker-round-six-6 --base-hash
630e43f95d646691767147aa56a9e8dee726037a37b5de5cfb5bbddee9c882f7` failed twice
with `node is claimed by worker with a different base hash`, so this resolution
proceeded under single-writer coordinator authority.
