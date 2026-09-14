---
context_rev: 1
priority: P2
updated: 2026-09-14T11:20:50Z
summary: Fix or dispose the round-ten Tangle FBK-031 findings.
next: "[[TAS-181-closure-names-resolved-sibling-seams]]"
---

Parent [[THO-027-round-ten-usage-feedback-analysis]].

# Context

Tangle `FBK-031` verified in the parent at `0.6.0+g169bad5`. Findings 4, 5, and 6
are project-local Tangle defects and are disposed. The remaining five are
contract-clarity or checker-lint changes.

# Outcome

Every confirmed round-ten finding is fixed or explicitly disposed, with contract
tests wherever a documented surface changes.

# Done when

- The coordination reference requires the brief to name the resolved-sibling
  compiler seams the approved change can force, and states that a mechanical
  compiler-forced edit to a resolved sibling's file is in the assigned closure.
- `SKILL.md` or the coordination reference requires every writer to stamp
  `updated` from the host clock and the coordinator to verify a future stamp at
  integration.
- The timed-out recovery section states the localized-red narrow-repair branch.
- The brief guidance requires a shared-stage invariant change to name an
  adversarial mixed-capability acceptance input.
- `braintree check` flags a `Gated on` line outside `# Context`.
- Every child is resolved or disposed with rationale.
- `make test` passes.

# Children

- [[TAS-181-closure-names-resolved-sibling-seams]] - Tangle `FBK-031` finding 1.
- [[TAS-182-worker-host-clock-stamp]] - Tangle `FBK-031` finding 2.
- [[TAS-183-localized-red-timeout-repair]] - Tangle `FBK-031` finding 3.
- [[TAS-184-brief-names-mixed-capability-case]] - Tangle `FBK-031` finding 7.
- [[TAS-185-check-gate-placement]] - Tangle `FBK-031` finding 8.
