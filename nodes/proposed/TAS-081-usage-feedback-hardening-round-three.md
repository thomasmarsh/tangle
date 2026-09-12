---
context_rev: 1
priority: P1
updated: 2026-09-12T16:56:33Z
summary: Fix or dispose the round-three Tangle usage-feedback findings across reversal semantics, frontier determinacy, checker link parsing, node addressing, the hash operand, and unresolved dependency representation.
next: "[[TAS-086-unresolved-dependency-representation]]"
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
