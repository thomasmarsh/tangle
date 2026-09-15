---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Fix or dispose the round-three Hekate usage-feedback findings across reversal semantics, frontier determinacy, checker link parsing, node addressing, the hash operand, and unresolved dependency representation.
---

# Context

Parent [[THO-011-round-three-usage-feedback-analysis]].

Findings N1-N8 verified in the parent against `0.5.0` (`64359e6`).

# Outcome

Every confirmed round-three finding is fixed or explicitly disposed, with
regression tests wherever behavior changes.

# Done when

- A reversed task outcome has a stated update-in-place versus supersession rule and commit traceability.
- The frontier answers either name the coordinator's deliberate frontier child or state that they return a candidate list.
- The plan-text gate status is stated.
- A wikilink-shaped token inside code is not a checker finding.
- The accepted node addressing and the exact hash operand are documented or implemented, and the frontier-transition ordering is stated.
- A dependency on an unresolved predecessor has a sanctioned representation and diagnostic.
- Every child is resolved or disposed with rationale.
- `make test` passes.

# Children

- [[TAS-082-reversal-semantics]] — N1.
- [[TAS-083-frontier-determinacy]] — N2 and N3.
- [[TAS-084-code-span-link-masking]] — N4.
- [[TAS-085-hash-addressing-and-operand]] — N5, N6, and N7.
- [[TAS-086-unresolved-dependency-representation]] — N8.

# Result

All five children are resolved, each with its contract text, regression tests,
and a passing gate; none needed a disposition or a supersession.

- [[TAS-082-reversal-semantics]] (N1, `9a7906f`): `SKILL.md` states the
  in-place-versus-supersession discriminator and the commit record a reversal
  owes the reversed direction; `test_skill_reversal_contract` pins it.
- [[TAS-083-frontier-determinacy]] (N2, N3, `3b1fff8`): the contract, the
  read-and-execute loop, and the verb help name the frontier answers as
  candidates resolved through the coordinator's `next` route, and a plan-text
  gate no node owns is `blocked`; `test_skill_frontier_candidate_contract`,
  `test_skill_plan_text_gate_status`, and the `_seed_upfront_plan` candidate
  tests pin both.
- [[TAS-084-code-span-link-masking]] (N4, `a8ecc9f`): `_mask_code` excludes
  inline code spans and fences from the link scan; the quoted-token and
  real-link regression cases and `test_skill_code_masking_status` pin it.
- [[TAS-085-hash-addressing-and-operand]] (N5, N6, N7, `6b3e348`): NODE
  addressing, the `content_hash` operand, and the frontier-transition ordering
  are stated next to each command and in the worktree contract, and
  `_unknown_node` names the accepted forms; the addressing, operand, and
  contract tests pin them.
- [[TAS-086-unresolved-dependency-representation]] (N8, `9fa63b6`): the
  unpinned `Gated on` line is the sanctioned representation and both
  context-edge diagnostics name it; the gate, diagnostic, and contract tests
  pin it.

Re-verified against the landed tree: each child's `# Done when` bullet holds,
`braintree hash` rejects a path and names the accepted forms, the checker masks
quoted link-shaped tokens while still reporting a real broken link, a gated
edge to a proposed target passes while both unresolved-target diagnostics name
the gate, and `braintree stale` reports no stale pins.

Evidence:

- `make test` passes (286 tests) and `braintree check nodes` passes (104 nodes).
