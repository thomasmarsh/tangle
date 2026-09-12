---
context_rev: 1
priority: P1
updated: 2026-09-12T14:02:27Z
summary: Fix or dispose the six confirmed round-two Tangle usage-feedback findings across the skill contract, graph-check, and bt.
next: [[TAS-062-release-mismatch-signal]]
---

# Context

Parent [[THO-009-second-round-usage-feedback-analysis]].

Findings R1-R6 verified in the parent against `0.4.0` (`e77839c`).

# Outcome

Every confirmed round-two finding is fixed or explicitly disposed, with
regression tests wherever behavior changes.

# Done when

- A semantic `context_rev` bump has a documented, committable shape that passes the mandated checker.
- `SKILL.md` states the knowledge-node frontier rule.
- The claim base-hash algorithm is documented and obtainable from `bt`.
- A mismatched `bt release` fails loudly instead of reporting a silent `no-op`.
- A pinned dependency that is not `resolved` is surfaced by the tooling or explicitly exempted.
- A mechanical change has a sanctioned commit path.
- `make test` passes with regression tests for each behavior change.
- Every child is resolved or disposed with rationale.
