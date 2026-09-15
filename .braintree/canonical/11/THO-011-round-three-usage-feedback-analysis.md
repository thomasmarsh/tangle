---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Round-three Hekate feedback confirms seven findings at 0.5.0 (64359e6) across reversal semantics, frontier determinacy, checker link parsing, node addressing, the hash operand, and unresolved dependency representation.
---

# Question

Area [[IDX-001-execution-graph]].

The Hekate vault recorded friction after the round analyzed in
[[THO-009-second-round-usage-feedback-analysis]]: the resolved notes
`THO-010-braintree-friction-release-profile-reversal`,
`THO-011-braintree-friction-phase-2-decomposition`,
`THO-012-braintree-friction-phase-2-increment-0`, and
`THO-013-braintree-friction-phase-1-increment-1`, plus the proposed feedback
nodes `FBK-001-braintree-check-nodes-failed-with-invalid-or-mis` and
`FBK-002-braintree-hash-rejects-a-node-path-with-a-bare-u`. Their ids collide
with this vault's own `THO`-`FBK` numbering, so they are cited as
`Hekate THO-0NN` and `Hekate FBK-00N`. Which findings still hold against this
implementation at `0.5.0` (`64359e6`), and what self-improvement work do they
require?

# Conclusion

Seven findings reproduce; two prior findings are already fixed and three are
consuming-side only. Reproduction used, in addition to the real vault, an
isolated probe vault in `/tmp/bt-probe` with `BT_SIDECAR_DIR`/`BT_PROJECT_ID`,
so no reservation state was disturbed.

| # | Finding | Source | Kind | Severity | Evidence |
|---|---------|--------|------|----------|----------|
| N1 | Reversing an outcome after partial implementation has no stated rule for update-in-place versus `disposition: superseded`, nor for what the resolved node owes a commit that named the old direction | Hekate THO-010 F1 | docs | medium | `SKILL.md` mutation rules state "prefer updating" and define `superseded`, but the reversal paragraph the source proposes does not exist |
| N2 | `braintree frontier`, `braintree next --rank`, and `braintree orient` report every unfinished node whose `next` is an action, so a coordinator's sequenced-but-not-frontier `proposed` siblings appear as equal frontier candidates | Hekate THO-011 F1, Hekate THO-012 F2 | tooling/docs | high | Probe: coordinator `next` names one child, yet all four action-`next` nodes (two children, two unrelated `THO`) print with no distinguishing mark; `SKILL.md` says `proposed` work is "not yet at the frontier" |
| N3 | There is no stated status for work gated on prerequisite plan text that no node owns | Hekate THO-012 F4 | docs | medium | `SKILL.md` contrasts `blocked` (external state, credential, approval) with `proposed` (ready but not frontier, or a sibling decision) but not a plan-text gate |
| N4 | The checker parses wikilink-shaped tokens inside inline code spans and fenced code blocks as real links, so a node quoting the skill's own grammar fails | Hekate THO-011 F4, Hekate THO-008 F2 | checker | medium | Probe: one inline and one fenced quoted token produced two `broken link` findings; the checker scans raw text without masking code |
| N5 | Node addressing is undocumented next to the commands and the worktree handoff says "node path": `braintree hash nodes/proposed/X.md` fails while `braintree hash X` succeeds | Hekate THO-012 F1, Hekate THO-013 F2, Hekate FBK-002 | docs/tooling | low | Probe: path form prints `unknown node`; the `help` line already names the accepted forms, but `SKILL.md` and the handoff do not state which operand the tool takes |
| N6 | `braintree hash` prints a labelled two-line object, while `SKILL.md` says it "prints the base hash" and to pass "that same starting value"; the claim accepts the whole two-line string as an opaque operand | Hekate THO-013 F1 | docs/tooling | medium | Probe: `braintree hash X` prints `node:` plus `content_hash:`; `claim --base-hash` accepted both the whole block and the bare digest, so the recorded value is ambiguous |
| N7 | The skill does not order the frontier transition against the claim, so it is unspecified whether the status move and `# Context` edit precede the claim or belong to the claimed edit, and which content "base hash" names | Hekate FBK-002 | docs | medium | `SKILL.md` says a worker hashes and claims "before editing" and that resolving a frontier child advances the parent, but never says whether a node's own `proposed`-to-`active` move is that first edit |
| N8 | A `Depends on` edge to an unresolved predecessor has no sanctioned representation: an unpinned edge fails as a missing pin and a pinned edge fails as unresolved | Hekate FBK-001 | docs/checker | medium | Probe: both forms are rejected with generic diagnostics and neither names the sanctioned gated form |

Already fixed (disposed, no work required):

- Hekate THO-010 F2, recurring `braintree allocate` collision: `allocate THO`
  on a vault holding `THO-001` and `THO-002` returned `THO-003`, so
  [[TAS-045-id-reservation-reconciliation]] holds.
- Hekate THO-011 F2, read loop pointing at an absent index-map recipe: the loop
  now runs the `braintree frontier` verb and no longer depends on a vault recipe.

Consuming-side only (disposed):

- Hekate THO-011 F3, Hekate THO-012 F3, and Hekate THO-013 F3, the divergence
  between the skill's `FBK` marker and the project's `THO` friction mechanism,
  is resolved in the consuming project: Hekate's `AGENTS.md` now mandates
  `braintree feedback record` and the `FBK` node it writes.

# Decision

Create the coordinating task [[TAS-081-usage-feedback-hardening-round-three]]
with one child per independently resumable confirmed change:

- [[TAS-082-reversal-semantics]] — N1.
- [[TAS-083-frontier-determinacy]] — N2 and N3.
- [[TAS-084-code-span-link-masking]] — N4.
- [[TAS-085-hash-addressing-and-operand]] — N5, N6, and N7.
- [[TAS-086-unresolved-dependency-representation]] — N8.

N2 is the highest-severity finding: the direct-answer verbs the current thrust
landed disagree with the documented frontier definition, so a fresh worker can
select a sequenced sibling.
