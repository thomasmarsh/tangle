---
context_rev: 1
priority: P2
updated: 2026-09-12T16:56:33Z
summary: Node addressing and the hash operand are documented next to hash, claim, and release and in the worktree contract, and a path-shaped unknown-node error names the accepted forms.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N5: the worktree handoff gives a worker a direct node path, but `braintree hash`
rejects a path and accepts only a bare ID or filename stem, and `SKILL.md` never
states the accepted form. N6: `braintree hash` prints a labelled two-line
object while the skill calls it "the base hash" and says to pass "that same
starting value"; the claim accepts either the whole block or the bare
`content_hash` as an opaque operand, so the recorded value is ambiguous. N7: the
skill says to hash and claim before editing but never says whether a node's own
frontier transition (the status move and `# Context` edit that takes the
frontier) precedes the claim or belongs to the claimed edit, and which content
the recorded base hash names.

# Outcome

One documented, unambiguous hash and claim contract.

# Done when

- `braintree hash`, `claim`, and `release` accept the node path the handoff gives a worker, or `SKILL.md` states the accepted forms next to each command and in the worktree contract.
- `braintree hash` prints a bare digest, or `SKILL.md` states that the `content_hash` field is the operand and shows it in the hash, claim, and release examples.
- `SKILL.md` states whether the frontier transition precedes the claim or is part of the claimed edit, and which content the base hash names.
- A path-shaped unknown-node error suggests the accepted forms.
- Regression tests cover the chosen addressing and operand behavior and `make test` passes.

# Result

Took the documentation branch for N5, N6, and N7, plus the error-path change the
addressing bullet requires.

- N5 addressing: `SKILL.md` states the accepted NODE forms next to the
  hash/claim/release commands and in the parallel-worktree handoff. NODE is a
  bare ID (`TAS-085`) or the full node name, the filename stem
  (`TAS-085-hash-addressing-and-operand`); a path is not accepted. `hash`
  resolves either form, while `claim` and `release` never read Markdown and
  treat NODE as the same opaque claim key, so one node is addressed with one
  spelling. `braintree hash nodes/proposed/X.md` still fails, but the
  `unknown node` help now derives the bare ID and full node name from the path
  and names them. The shared `_unknown_node` helper carries the same suggestion
  for `hash`, `backlinks`, `node`, and `impact`.
- N6 operand: `SKILL.md` states that the `content_hash` field is the operand, a
  bare 64-character digest passed as `--base-hash`, never the
  `node:`/`content_hash:` block, and shows it in hash, claim, and release
  examples.
- N7 ordering: `SKILL.md` states that a worker hashes and claims before editing,
  that the node's own frontier transition (the status move and the `# Context`
  edit that take the frontier) is part of the claimed edit rather than a
  precondition, and that the recorded `content_hash` names the node content
  exactly as handed off, before that transition and before any other edit.

Evidence:

- `test_hash_rejects_a_path_and_names_the_accepted_forms` and
  `test_hash_content_hash_is_the_claim_and_release_operand` pin the addressing
  and operand behavior.
- `test_skill_hash_addressing_and_operand_contract` pins the `SKILL.md` strings,
  including the worktree wording.
- `make test` and `braintree check nodes` pass.
