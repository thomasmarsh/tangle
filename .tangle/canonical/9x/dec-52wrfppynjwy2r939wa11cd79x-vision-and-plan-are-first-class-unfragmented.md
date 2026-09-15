---
context_rev: 1
status: resolved
updated: 2026-09-15T16:55:29Z
summary: VISION and PLAN are first-class unfragmented authorities; the graph owns execution state.
---

Area [[IDX-001-execution-graph]].

# Context

Owner policy answer to [[TAS-169-settle-plan-graph-authority]], grounded in the
project-declared authority boundary of [[TAS-168-characterize-legacy-plans]] and
the first-class hierarchical-document intuition in `NOTES.md`. The owner decided
how planning documents coexist with the execution graph.

# Decision

VISION and PLAN documents are first-class in the vault. They may live inside the
vault or outside it (for example `../doc/foo.md`), and they may refer to one
another. They are not ingested, fragmented, mirrored, or decomposed into nodes;
they remain authoritative for their own unfragmented purpose -- vision,
narrative, requirements, and plan-level intent -- and Tangle does not take
ownership of that material.

The execution graph remains authoritative for admitted execution state: node
status, `next`, blockers, dependencies, and pinned operative decisions. A node
cites a VISION or PLAN document or one of its sections; it does not copy that
content into graph authority.

Tangle cannot constrain how a project edits, versions, or otherwise uses its
planning documents. Enforcement is limited to what the graph can check.

# Rationale

- [[TAS-168-characterize-legacy-plans]] established that source role, authority,
  identity, retrieval, and handling are project-declared rather than inferred.
  First-class owner-declared planning documents are the direct expression of
  that model.
- Fragmentation serves token-bounded execution memory; a VISION or PLAN serves
  unfragmented reading by humans and whole-plan consumers. Different roles, so
  keeping both creates no two-editable-owners conflict.
- Tangle enforcing planning-document rules would constrain workflows it cannot
  observe or own; graph-local enforcement is the only checkable boundary.

# Consequences

- Permanent coexistence is the model, not a migration stage. Archived-plan
  migration, full migration, and a plan-led overlay are not the recommended
  default; where a project chooses ingestion or conversion, it is an optional
  project-local workflow and never a precondition.
- A planning document is never forced read-only, never mutated by Tangle, and
  never synchronized back from the graph. Any graph-to-plan projection is
  derived and never an independent authority.
- Requirements and acceptance criteria may stay authoritative in their
  unfragmented document; once work is admitted, its status, `next`, blockers,
  and dependencies belong to the graph.
- The plan-intake children [[TAS-170-define-plan-bridge-contract]] through
  [[TAS-178-build-derived-plan-renderer]] were authored on an ingestion-intake
  premise (bridge, pilot, analyzer, drift, renderer). Each needs re-scoping to
  the first-class-document default or deliberate disposition; that
  reconciliation is the remaining action of [[TAS-169-settle-plan-graph-authority]].
- [[THO-026-how-should-living-planning-documents-coexist-wit]]'s
  staged-hybrid-bridge hypothesis is answered: the documents stay first-class,
  and the graph enforces only execution state.
- Representing and resolving a first-class VISION/PLAN document that is not a
  node (vault-relative or external path, cross-references) is follow-on
  implementation work with no owning node yet.
