---
status: resolved
context_rev: 2
updated: 2026-09-14T23:40:13Z
summary: Characterize project-neutral planning-material variability and discovery needs.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Tangle is infrastructure used by unrelated projects, not an intake mechanism for a known corpus. Planning material may be absent, singular, distributed, generated, remotely hosted, indirectly addressable, structured or unstructured, mutable or immutable, public or restricted, and connected to arbitrary human and machine workflows. Its role, authority, lifecycle, audience, handling policy, and relationship to execution may be unique to the consuming project.

No particular source path, repository layout, document role, authority class, format, section structure, audience, integration, or preservation strategy is therefore a prerequisite or a default. Concrete examples may falsify or refine the model, but they cannot define the supported universe.

# Outcome

A project-neutral variability and discovery model identifies what Tangle may rely on universally, what each consuming project must declare or expose, and how intake must behave when a source property or required capability is unknown.

# Done when

- The model covers open-ended variation in source discovery and identity, cardinality and relationships, role and authority, lifecycle and mutability, format and structure, audience and access, handling and retention, integrations, and project-specific semantics without treating any listed value as exhaustive.
- It separates Tangle's universal invariants from source-specific facts that must be supplied, discovered through an explicit capability, or left unknown.
- It defines safe behavior for unknown or unsupported properties: surface the uncertainty, request project-local policy when necessary, and preview, defer, or decline work instead of silently inferring authority or destructive handling.
- It treats possible content categories and failure modes as non-exhaustive observations rather than a required document schema; no category must exist, map to a section, or receive a predetermined graph disposition.
- A scenario matrix uses synthetic, adapted, or optionally volunteered real examples to challenge the model across materially different combinations; no specific corpus, path, repository, or permission to preserve source material is required to complete the task.
- The result audits downstream authority, bridge, pilot, analyzer, drift, and rendering work for assumptions about paths, Git, text sections, fixed roles, formats, audiences, integrations, or handling constraints and records the requirements those nodes must satisfy.
- Evaluation criteria distinguish general intake costs from project-local measures, including discovery burden, cold resumption, source access, authority conflict, reconciliation, and dual maintenance.

# Result

`research/planning-material-intake-model.md` records the full model: nine open-ended variability axes; a five-class epistemic partition (universal, project-declared, discoverable, unknown, unsupported) that decides intake behavior per property rather than per document; a safe-behavior protocol for unknown and unsupported properties with an explicit forbidden-inference list; content categories and failure modes stated as non-exhaustive observations rather than a schema; an eight-scenario matrix of synthetic and adapted shapes requiring no corpus, path, repository, or preserved source; a downstream audit naming the assumptions and requirements for [[TAS-169-settle-plan-graph-authority]], [[TAS-170-define-plan-bridge-contract]], [[TAS-171-pilot-incremental-plan-intake]], [[TAS-173-decide-plan-analyzer-surface]]/[[TAS-174-build-dry-run-plan-analyzer]], [[TAS-175-decide-source-drift-policy]]/[[TAS-176-build-source-drift-reconciliation]], and [[TAS-177-decide-derived-plan-rendering]]/[[TAS-178-build-derived-plan-renderer]]; and evaluation criteria split into comparable general intake costs and project-declared local measures.

The model settles the discovery boundary the authority and bridge nodes gate on: source role, authority, identity, retention, and handling are project-declared or explicitly unknown, never inferred from source shape, size, age, or format. No source path, Git, text-section, or fixed-role assumption survives the audit.
