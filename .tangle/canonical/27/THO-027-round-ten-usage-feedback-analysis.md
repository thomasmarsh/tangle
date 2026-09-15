---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Round-ten Hekate feedback admits five changes and disposes three project-local findings.
---

Area [[IDX-001-execution-graph]].

# Question

`tangle feedback scan /Users/thomasmarsh/git/hekate` reports one proposed
feedback node recorded after the round analyzed in
[[THO-025-round-nine-usage-feedback-analysis]]: Hekate `FBK-031`, recorded at
`0.6.0+g169bad5` and carrying eight findings. Which findings still hold against
this implementation at that revision, which are duplicates or already admitted,
and what self-improvement work do they require?

# Context

The installed revision `0.6.0+g169bad5` already contains every round-eight
remediation ([[TAS-153-usage-feedback-hardening-round-eight]]), so findings 1, 2,
and 3 are recurrences that show the round-eight rules were necessary but not
sufficient. `SKILL.md`, `references/coordination.md`, and
`src/tangle/graph_check.py` are byte-identical between `169bad5` and the
current tree, so the same verdicts apply. Verified with exact `rg` searches and a
`tangle check` probe of a scratch vault; no reservation or vault state was
disturbed.

# Conclusion

| Feedback | Verdict | Evidence |
|----------|---------|----------|
| Hekate `FBK-031` finding 1 | open residual, admitted | Round eight [[TAS-158-write-set-closure-generators-and-manifests]] added exhaustive matches and struct literals to the closure, yet four of eleven leaves still needed a resolved sibling's file and three workers stopped to ask. The rule does not require the coordinator to name those resolved-sibling compiler seams in the brief, and a mechanical compiler-forced edit to a resolved sibling's file reads as an owned-seam escalation. |
| Hekate `FBK-031` finding 2 | open residual, admitted | Recurrence of Hekate `FBK-026` finding 4 and the third session to record it. `SKILL.md` requires the coordinator to stamp the host clock and a worker to clamp an inherited future `updated`, but never requires a worker's own fresh `updated` to come from the host clock nor the coordinator to verify one at integration. |
| Hekate `FBK-031` finding 3 | open refinement, admitted | The round-eight `## Timed-out worker recovery` procedure treats every non-green partial as revert-and-re-scope. A partial that is red on one localized, understood case while the rest is green is not covered, so a blanket revert discards near-complete work. |
| Hekate `FBK-031` finding 4 | disposed, project-local | The reference-tangent versus travel-heading frame mismatch and the indirect `Infeasible { limiting: BandEdge }` verdict are Hekate kernel and contract defects; admitting them would create nodes this repository cannot resolve. |
| Hekate `FBK-031` finding 5 | disposed, project-local | `file:line` citation rot in Hekate `docs/schema-v2-contract.md` and the proposed citation doctor are Hekate documentation and tooling; this repository has no line-number citation convention to harden. |
| Hekate `FBK-031` finding 6 | disposed, project-local | `CompiledFacilityAdjacency` lacking a per-adjacency cross-band offset is a Hekate model and kernel gap. The definition-completeness principle it restates is already owned by round seven [[TAS-143-definition-completeness-for-deferred-shapes]]. |
| Hekate `FBK-031` finding 7 | open, admitted | `rg -in 'adversarial\|mixed-capability\|shared stage\|acceptance input' SKILL.md references/` matches nothing: a shared-stage invariant change is not required to exercise an existing participant that lacks the new state. |
| Hekate `FBK-031` finding 8 | open residual, admitted | Probe: a `Gated on [[TAS-901-probe]]` line in a scratch node's `# Outcome` passes `tangle check` with zero findings, because the checker scans only the pinned context relations. The `next` form rules are already enforced by `next-action-wikilink` and `next-not-direct-child`, so only the gate structure is missing. |

Disposed without admission:

- Hekate `FBK-031` findings 4, 5, and 6 are Hekate-project kernel defects,
  contract documentation, and model gaps; admitting them would create nodes this
  repository cannot resolve.

# Decision

Create the coordinating task
[[TAS-180-usage-feedback-hardening-round-ten]] with one child per independently
resumable confirmed change:

- [[TAS-181-closure-names-resolved-sibling-seams]] - Hekate `FBK-031` finding 1.
- [[TAS-182-worker-host-clock-stamp]] - Hekate `FBK-031` finding 2.
- [[TAS-183-localized-red-timeout-repair]] - Hekate `FBK-031` finding 3.
- [[TAS-184-brief-names-mixed-capability-case]] - Hekate `FBK-031` finding 7.
- [[TAS-185-check-gate-placement]] - Hekate `FBK-031` finding 8.

The round is `P2`; all five are contract-clarity or checker-lint changes that
block no other work.
