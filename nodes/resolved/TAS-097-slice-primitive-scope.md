---
context_rev: 1
priority: P2
updated: 2026-09-12T21:47:18Z
summary: State whether a worker may author the minimal primitive or seam a slice gate needs inside its declared write set, and when it must escalate.
---

# Context

Parent [[TAS-095-usage-feedback-hardening-round-four]].

Tangle `FBK-003` at `0.5.0+g64359e6`: an assigned slice whose gate required an
authored stop line and a spawn admission the compiled model did not provide,
while the write set covered only two packages. Neither `SKILL.md` nor the node
said whether a gate's needed primitive is in-scope authoring, a new node, or an
escalation, so the worker stopped mid-slice twice. Reproduced in
[[THO-013-round-four-usage-feedback-and-portfolio-analysis]] by reading the
contract: the parallel-worktree section names the write set, its verification,
and the handoff report, but no authoring rule, and no text matches `primitive`
or `seam`.

# Outcome

A worker continuing an assigned slice knows that a minimal primitive or seam
its gate or Done-when criterion needs is in-scope authoring inside the declared
write set, and which boundary instead requires escalation, so it does not stop
mid-slice to ask.

# Done when

- `SKILL.md` states that a worker may author the minimal primitive or seam a gate or Done-when criterion needs inside its declared write set, and records it in the node's result.
- `SKILL.md` states the escalation boundary: a change that alters a landed seam another node owns, or the public schema contract, is escalated rather than authored.
- `SKILL.md` states that a coordinating task names any primitive or seam its slice must introduce, so the worker does not have to infer it.
- A `SKILL.md` contract test pins the stated rule and `make test` passes.

# Result

Resolved. `SKILL.md` now carries the slice-authoring rule as a bullet in the
parallel-worktree contract: a worker may author the minimal primitive or seam a
gate or `Done when` criterion needs inside its declared write set and records
that authored piece in the node's `# Result`; a change that alters a landed seam
another node owns, or the public schema contract, is escalated rather than
authored; and a coordinating task names any primitive or seam its slice must
introduce, so the worker does not have to infer it.

`tests/test_skill.py` pins the rule with `test_skill_slice_primitive_scope_contract`
over `_SLICE_PRIMITIVE_SCOPE_CONTRACT`, asserting the authoring scope, the
`# Result` disclosure, the escalation boundary, and the coordinator's naming
obligation.

## Limitations

Documentation and contract-test only: no runtime behavior changes, and the
escalation channel itself is unchanged. The rule states the boundary; it does
not enforce it in `braintree check`.

## Evidence

- `braintree check nodes` -> `graph check: passed (123 nodes)`.
- `uv run pytest tests/test_skill.py -k "slice_primitive or parallel_contract" -q` -> `2 passed, 23 deselected`.
- `make test` -> `379 passed, 3 skipped`, ruff and mypy clean, worktree-parallel and install suites passed.
