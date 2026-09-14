---
context_rev: 2
priority: P2
updated: 2026-09-14T11:55:07Z
summary: Fix or dispose the round-ten Tangle FBK-031 findings.
next: "[[TAS-183-localized-red-timeout-repair]]"
---

Parent [[THO-027-round-ten-usage-feedback-analysis]].

# Context

Tangle `FBK-031` verified in the parent at `0.6.0+g169bad5`. Findings 4, 5, and 6
are project-local Tangle defects and are disposed. The remaining five are
contract-clarity or checker-lint changes.

A post-admission boundary review retains five leaves. TAS-181 governs whether a
compiler-forced edit is authorized inside a worker's write-set closure;
TAS-184 governs whether a shared-stage change has an acceptance input capable of
falsifying a uniform-capability assumption. They share documentation and test
paths, but have independent acceptance and rollback boundaries and preserve
different feedback evidence, so they stay separate and execute serially:
TAS-181, then TAS-184. The other three leaves change distinct mutation,
recovery, and graph-check contracts.

# Outcome

Every confirmed round-ten finding is fixed or explicitly disposed, with contract
tests wherever a documented surface changes.

# Done when

- The coordination reference requires the brief to name the resolved-sibling
  compiler seams known before dispatch, resolves the precedence between closure
  membership and resolved-sibling ownership, and keeps semantic seam changes as
  escalations.
- The brief guidance requires a shared-stage change that assumes participant
  state or capability to name a mixed-capability acceptance input and its
  expected behavior.
- `SKILL.md` or the coordination reference requires every writer to read the
  host clock for a fresh `updated`, and requires integration to distinguish and
  repair a fresh future stamp without moving an inherited future stamp backward.
- The timed-out recovery section states a bounded, evidence-based localized-red
  narrow-repair branch and preserves revert-and-re-scope as the fallback.
- `braintree check` flags a `Gated on` line outside `# Context`.
- Every child is resolved or disposed with rationale.
- `make test` passes.

# Children

- [[TAS-181-closure-names-resolved-sibling-seams]] - Tangle `FBK-031` finding 1.
- [[TAS-184-brief-names-mixed-capability-case]] - Tangle `FBK-031` finding 7.
- [[TAS-182-worker-host-clock-stamp]] - Tangle `FBK-031` finding 2.
- [[TAS-183-localized-red-timeout-repair]] - Tangle `FBK-031` finding 3.
- [[TAS-185-check-gate-placement]] - Tangle `FBK-031` finding 8.
