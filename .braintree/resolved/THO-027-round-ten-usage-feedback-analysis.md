---
context_rev: 1
updated: 2026-09-14T11:20:25Z
summary: Round-ten Tangle feedback admits five changes and disposes three project-local findings.
---

Area [[IDX-001-execution-graph]].

# Question

`braintree feedback scan /Users/thomasmarsh/git/tangle` reports one proposed
feedback node recorded after the round analyzed in
[[THO-025-round-nine-usage-feedback-analysis]]: Tangle `FBK-031`, recorded at
`0.6.0+g169bad5` and carrying eight findings. Which findings still hold against
this implementation at that revision, which are duplicates or already admitted,
and what self-improvement work do they require?

# Context

The installed revision `0.6.0+g169bad5` already contains every round-eight
remediation ([[TAS-153-usage-feedback-hardening-round-eight]]), so findings 1, 2,
and 3 are recurrences that show the round-eight rules were necessary but not
sufficient. `SKILL.md`, `references/coordination.md`, and
`src/braintree/graph_check.py` are byte-identical between `169bad5` and the
current tree, so the same verdicts apply. Verified with exact `rg` searches and a
`braintree check` probe of a scratch vault; no reservation or vault state was
disturbed.

# Conclusion

| Feedback | Verdict | Evidence |
|----------|---------|----------|
| Tangle `FBK-031` finding 1 | open residual, admitted | Round eight [[TAS-158-write-set-closure-generators-and-manifests]] added exhaustive matches and struct literals to the closure, yet four of eleven leaves still needed a resolved sibling's file and three workers stopped to ask. The rule does not require the coordinator to name those resolved-sibling compiler seams in the brief, and a mechanical compiler-forced edit to a resolved sibling's file reads as an owned-seam escalation. |
| Tangle `FBK-031` finding 2 | open residual, admitted | Recurrence of Tangle `FBK-026` finding 4 and the third session to record it. `SKILL.md` requires the coordinator to stamp the host clock and a worker to clamp an inherited future `updated`, but never requires a worker's own fresh `updated` to come from the host clock nor the coordinator to verify one at integration. |
| Tangle `FBK-031` finding 3 | open refinement, admitted | The round-eight `## Timed-out worker recovery` procedure treats every non-green partial as revert-and-re-scope. A partial that is red on one localized, understood case while the rest is green is not covered, so a blanket revert discards near-complete work. |
| Tangle `FBK-031` finding 4 | disposed, project-local | The reference-tangent versus travel-heading frame mismatch and the indirect `Infeasible { limiting: BandEdge }` verdict are Tangle kernel and contract defects; admitting them would create nodes this repository cannot resolve. |
| Tangle `FBK-031` finding 5 | disposed, project-local | `file:line` citation rot in Tangle `docs/schema-v2-contract.md` and the proposed citation doctor are Tangle documentation and tooling; this repository has no line-number citation convention to harden. |
| Tangle `FBK-031` finding 6 | disposed, project-local | `CompiledFacilityAdjacency` lacking a per-adjacency cross-band offset is a Tangle model and kernel gap. The definition-completeness principle it restates is already owned by round seven [[TAS-143-definition-completeness-for-deferred-shapes]]. |
| Tangle `FBK-031` finding 7 | open, admitted | `rg -in 'adversarial\|mixed-capability\|shared stage\|acceptance input' SKILL.md references/` matches nothing: a shared-stage invariant change is not required to exercise an existing participant that lacks the new state. |
| Tangle `FBK-031` finding 8 | open residual, admitted | Probe: a `Gated on [[TAS-901-probe]]` line in a scratch node's `# Outcome` passes `braintree check` with zero findings, because the checker scans only the pinned context relations. The `next` form rules are already enforced by `next-action-wikilink` and `next-not-direct-child`, so only the gate structure is missing. |

Disposed without admission:

- Tangle `FBK-031` findings 4, 5, and 6 are Tangle-project kernel defects,
  contract documentation, and model gaps; admitting them would create nodes this
  repository cannot resolve.

# Decision

Create the coordinating task
[[TAS-180-usage-feedback-hardening-round-ten]] with one child per independently
resumable confirmed change:

- [[TAS-181-closure-names-resolved-sibling-seams]] - Tangle `FBK-031` finding 1.
- [[TAS-182-worker-host-clock-stamp]] - Tangle `FBK-031` finding 2.
- [[TAS-183-localized-red-timeout-repair]] - Tangle `FBK-031` finding 3.
- [[TAS-184-brief-names-mixed-capability-case]] - Tangle `FBK-031` finding 7.
- [[TAS-185-check-gate-placement]] - Tangle `FBK-031` finding 8.

The round is `P2`; all five are contract-clarity or checker-lint changes that
block no other work.
