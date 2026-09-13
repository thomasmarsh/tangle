---
context_rev: 1
priority: P1
updated: 2026-09-12T14:40:00Z
summary: Fix or dispose the six confirmed round-two Tangle usage-feedback findings across the skill contract, graph-check, and bt.
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

# Result

All six round-two findings are fixed with regression tests.

- R1 [[TAS-059-stale-pin-commit-shape]]: the documented staged-staleness commit
  shape for a semantic `context_rev` bump.
- R2 [[TAS-060-knowledge-node-frontier-advance]]: the knowledge-node frontier
  rule.
- R3 [[TAS-061-claim-hash-exposure]]: `bt hash NODE` and the documented
  base-hash algorithm.
- R4 [[TAS-062-release-mismatch-signal]]: a mismatched `bt release` fails
  loudly instead of reporting a silent `no-op`.
- R5 [[TAS-063-pinned-dependency-status-check]]: `graph-check` reports a pinned
  dependency that is not resolved.
- R6 [[TAS-064-mechanical-change-commit-path]]: a sanctioned non-node commit
  path for mechanical changes.

`make test` passes: 142 pytest tests plus lint, type checks, and the install
and worktree-parallel end-to-end suites.
