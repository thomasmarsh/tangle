---
context_rev: 2
updated: 2026-09-14T02:42:27Z
summary: Correct the planning-material intake model and remove premature policy.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Depends on [[TAS-168-characterize-legacy-plans]] at context_rev 2.

The resolved task produced `research/planning-material-intake-model.md`, but review found category errors, internal contradictions, unsupported universal claims, and downstream requirements that prematurely settle decisions owned by later nodes. This task corrects that derived artifact without reopening TAS-168.

# Outcome

The intake model accurately separates Braintree invariants, project decisions, observations, knowledge state, and capability support; challenges rather than pre-decides downstream choices; and gives pilots falsifiable evaluation guidance.

# Done when

- The nine variability axes named by TAS-168 are explicit and non-overlapping enough to audit.
- Policy authority, observable evidence, uncertainty, and capability support are modeled independently.
- Safe behavior is conditional on authorization and relevance, and does not equate read-only with permitted.
- Scenarios expose decision points without choosing downstream policy.
- Downstream handoffs constrain assumptions without deciding the authority, bridge, analyzer, drift, or renderer nodes.
- Evaluation criteria are measurable and are not mislabeled as current Braintree invariants.
- The corrected artifact and this task pass graph validation; the project owner
  has waived tests for this documentation-only correction.

# Result

Rewrote `research/planning-material-intake-model.md` after review falsified the
artifact committed by [[TAS-168-characterize-legacy-plans]]. The original model
treated governing policy, evidence source, knowledge state, and capability
support as one mutually exclusive epistemic partition; called unsettled product
choices universal invariants; prescribed outcomes owned by downstream decision
nodes; equated non-destructive access with safe access; replaced evidence
provenance with review rationale; and used scenarios that asserted their answers
instead of testing the model.

The regenerated artifact now presents the nine requested variability axes,
separates the five labels by dimension, gates operations on purpose, authority,
evidence, support, and admission, and distinguishes evidence lineage from
decision lineage. Its scenarios expose invalid inferences without selecting a
coexistence mode, identity mechanism, analyzer, drift policy, or renderer. Its
evaluation design separates contract checks, empirical measures with
denominators, and project acceptance thresholds.

`braintree check` passed with 215 nodes before resolution. The project owner
explicitly waived tests for this documentation-only correction. Downstream
consumers must reconcile against this correction rather than relying only on the
superseded artifact description in TAS-168.
