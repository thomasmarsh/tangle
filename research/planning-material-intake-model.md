# Project-neutral planning-material intake: variability and discovery model

## Purpose and scope

This document is the model of record for how Braintree relates to a consuming
project's *planning material* — the documents, tickets, notebooks, wikis, specs,
and generated plans that describe what a project intends to do before admitted
execution state exists. It answers one question: what may Braintree rely on
universally, what must each project declare or expose, what can be discovered
through an explicit capability, and what must be left unknown?

It serves the workstream headed by `TAS-167-legacy-plan-intake-lifecycle` and its
direct frontier child `TAS-168-characterize-legacy-plans`. It is deliberately a
model, not a schema: nothing here is a required document shape, a required
section, or a predetermined graph disposition. Concrete examples may falsify or
refine the model; they cannot define the supported universe, because Braintree is
infrastructure used by unrelated projects rather than an intake mechanism for a
known corpus.

Braintree's own contract is the fixed reference point, not the source material.
Markdown nodes under the status directories remain the only authority; `SKILL.md`
owns admission, boundaries, status, dependencies, and `context_rev`. This
document adds no authority and changes no invariant.

## Universal invariants

These hold for every project regardless of whether planning material exists, what
form it takes, or who owns it. They are the facts Braintree may rely on without
asking the consuming project.

1. **Source material is not project truth.** A long-lived or heavily edited
   document is not authoritative merely because it exists or predates the graph.
   Observation of a source is evidence for review, never admission.
2. **Intake is reviewed and outcome-based.** Node creation and node boundaries
   are decided by a reviewer against the durable-outcome rule, not by source
   headings, chunk boundaries, or inferred entities.
3. **One owner per mutable fact.** Once a fact is admitted, exactly one surface
   is authoritative for it. No fact has two editable owners.
4. **Retrieval is not admission.** A command may find, rank, or cite source
   spans automatically; it may never turn a heading, chunk, or inferred entity
   into an authoritative node.
5. **Uncertainty is surfaced, not resolved by inference.** When a source property
   or required capability is unknown, intake states the unknown and takes the
   non-destructive branch rather than guessing authority or handling policy.
6. **The graph is self-contained after admission.** A cold reader can resume
   admitted work from the vault without the source, network access, or hidden
   conversational context.
7. **Capabilities degrade explicitly.** An absent optional capability (semantic
   provider, Git, network) produces a stated no-op or abstention, never a silent
   best-effort result presented as authoritative.
8. **Destructive and authority-bearing actions require project-local policy.**
   Mutating a source, changing its authority class, or retiring a source is never
   a default.
9. **Provenance is the reviewed decision, not the source address.** A source
   span may be cited, but the durable reason a fact is admitted is the review
   that admitted it.

## The variability axes

The axes are open-ended. Each lists dimensions that have been observed or
plausibly arise; the list is illustrative and non-exhaustive, and no single value
is a default.

### 1. Source discovery and identity

- **Location:** in-repository, sibling checkout, shared filesystem, wiki or
  issue tracker, object store, remote URL, generated at build time, addressable
  only through a project tool, or absent.
- **Identity:** filesystem path, path plus revision, content hash, section hash,
  document id in an external system, or no stable id at all.
- **Stability:** immutable snapshot, append-only log, rewritten in place,
  regenerated on every run, or deleted and recreated.
- **Cardinality and relationships:** zero, one, or many sources; independent,
  parent/child, superseding, or mutually contradictory.

### 2. Role and authority

- Historical record; authoritative living specification; narrative rationale;
  requirements baseline; acceptance criteria; decision log; status checklist;
  backlog; generated projection; mixed and inconsistent roles.
- Authority may be document-level, section-level, or absent. It may change over
  time, and different readers may disagree about it.

### 3. Lifecycle and mutability

- Frozen and archived; actively rewritten; edited by humans, LLMs, or both;
  branched and merged; scheduled for deletion; retention-governed; already
  partially migrated into another system.

### 4. Format and structure

- Prose, headings, tables, checklists, diagrams, embedded code, notebooks,
  tickets, comment threads, binary or mixed-encoding documents, deeply nested
  structures, machine-generated text.
- Structure may be meaningful, decorative, or absent. No structure grants
  authority.

### 5. Audience and access

- Public, internal, restricted, credentialed, or per-reader. Access may be
  time-limited, audited, or unavailable to the agent entirely.

### 6. Handling and retention

- Must be preserved in place; may be copied; may be annotated; must not be
  mutated; must not leave its system of record; contains restricted content that
  may not be quoted or stored; subject to data-residency or retention rules.

### 7. Integrations and project-specific semantics

- Git hooks, CI, issue trackers, chat, LLM pipelines, documentation generators,
  or bespoke tools that read or write the source.
- Project-local meaning for terms, ownership, approval, and completion that
  Braintree does not define and must not presume.

## The epistemic partition

Every property relevant to intake falls into exactly one of five classes. The
partition is the operational core of this model: intake behavior is determined by
which class a property is in, not by the property's name.

| Class | Meaning | Who supplies it | Intake behavior |
| --- | --- | --- | --- |
| **Universal** | A Braintree invariant, above | Braintree | Rely on it unconditionally |
| **Project-declared** | A policy or authority fact only the project can choose | The consuming project | Require before authority-bearing or destructive action |
| **Discoverable** | An observable property obtainable through an explicit capability | A named capability | Observe it, cite it, but never let it confer authority |
| **Unknown** | Relevant but currently unspecified and not observable | No one yet | Surface it; take the non-destructive branch |
| **Unsupported** | Recognized but outside the supported surface | No one | Decline explicitly and record why |

Notes:

- The class is per property, not per document. A single source can have a
  discoverable format, a project-declared authority class, and an unknown
  retention policy at the same time.
- A discoverable property may never be promoted to project-declared by
  inference. "The file is Git-tracked" does not mean "the project accepts
  path-plus-revision identity," and "the document has an `## Acceptance
  criteria` heading" does not mean "that section is authoritative."
- An unknown may be promoted to project-declared only by an explicit project
  statement, or to discoverable only by naming and running a capability that
  yields it. Silence is never promotion.

## Safe behavior for unknown and unsupported properties

Intake that meets an unknown or unsupported property follows one protocol:

1. **Surface.** Record the property, its class, and why it matters in the intake
   record or bridge. Never let an unknown pass silently into a default.
2. **Classify the decision.** Is the next action non-destructive and
   authority-neutral (extract, cite, preview, defer) or is it destructive or
   authority-bearing (mutate the source, declare an authority class, admit a
   node whose boundary depends on the unknown)?
3. **Act on the safe branch.** For non-destructive work, proceed with a preview
   or a bounded extraction that does not depend on the unknown. For
   authority-bearing or destructive work, request project-local policy and wait.
4. **Degrade explicitly.** If a required capability is absent, abstain with a
   stated reason instead of approximating.
5. **Record the outcome.** Whether the work proceeded, deferred, or declined,
   the reason and the unknown are durable so the next reader does not re-derive
   them.

Forbidden under all circumstances, because each silently infers authority or
performs destructive handling:

- Treating a source's existence, length, or age as authority.
- Choosing a node boundary from a heading, chunk, or embedding cluster.
- Persisting an inferred entity, summary, or classification as project truth.
- Writing to, annotating, freezing, or deleting a source without explicit
  project-local permission.
- Quoting or storing restricted content the project has not cleared for storage.
- Presenting a degraded or partial read as a complete one.

## Content categories and failure modes are observations, not a schema

The categories below are useful for review and for designing scenarios. None is
required to exist in any source. None maps to a required section. None carries a
predetermined graph disposition. A source may contain all, some, or none of them,
and the same category may warrant different handling in different projects.

Observable content categories:

- Narrative rationale and history.
- Future work that is not yet admitted.
- Requirements and acceptance criteria.
- Operative decisions consumers must pin.
- Status and checklists (mutable execution state).
- Speculative or exploratory branches.
- Completed work and its evidence.
- Contradictions and duplicated owners.

Observable failure modes:

- Contradictory sections or duplicated owners.
- Speculative work presented as planned work.
- Stale checklists that disagree with reality.
- Content the project may not store or quote.
- Non-text, mixed-encoding, or unreachable sources.
- Very large or continuously regenerated documents.
- Version churn that rewrites headings and prose.

Treating any item above as mandatory — requiring a section to exist, or fixing a
disposition for a category — is a defect in the intake contract, not a
simplification of it.

## Scenario matrix

The following synthetic and adapted scenarios challenge the model across
materially different combinations. They are illustrative. No specific corpus,
path, repository, or permission to preserve source material is required to
complete this work, and the list is non-exhaustive.

| ID | Source shape | Authority | Access | Expected partition outcome | Safe behavior |
| --- | --- | --- | --- | --- | --- |
| S1 | Single immutable Markdown snapshot in-repo | Historical | Public | All properties known; snapshot mode | Stamp identity; extract only current frontier; leave source read-only |
| S2 | Living spec rewritten by an LLM, Git-tracked, public | Living narrative + spec | Public | Authority class project-declared; identity discoverable | Hybrid mode; bridge; one-way derived views; never mirror status back |
| S3 | Plans spread across wiki, issue tracker, notebooks | Mixed, partly contradictory | Restricted | Cardinality and authority unknown | Surface unknowns; request policy; preview only; decline node admission |
| S4 | No planning material at all | None | n/a | Only universal invariants apply | Ordinary just-in-time decomposition; no intake machinery exercised |
| S5 | Machine-generated plan regenerated on each build | Derived projection | Internal | Identity and lifecycle discoverable; authority project-declared | Treat as derived, never authority; re-derive; do not hand-edit |
| S6 | Living plan with contradictions and stale checklist | Disputed | Internal | Contradictions observable; authority unknown | Pilot stress case; record conflicts; defer admission pending review |
| S7 | Remote, credentialed, access-gated, not Git-tracked | Unknown | Credentialed | Identity discoverable via content hash; retention unknown | Content-hash identity; request retention policy; never store restricted spans |
| S8 | Binary or deeply nested generated structures | Unknown | Restricted | Format discoverable as unsupported | Decline explicitly with reason; do not lossily convert as if faithful |

## Downstream audit: assumptions and requirements

Each downstream node must not assume a fixed value on a variability axis. This
audit records the assumptions to check and the requirement each node must
satisfy. It is the requirements hand-off `TAS-168`'s `Done when` names.

### `TAS-169-settle-plan-graph-authority`

- **Assumptions to audit:** that a source has one fixed role; that narrative,
  requirements, and acceptance criteria have an inherent owner; that hybrid
  operation is always a migration stage.
- **Requirement:** the authority matrix must be keyed by project-declared
  coexistence mode, define exactly one owner per mutable fact in snapshot,
  living-specification, and full-migration modes, support permanent hybrid
  operation as a first-class choice, and never require Git or a fixed document
  schema.

### `TAS-170-define-plan-bridge-contract`

- **Assumptions to audit:** that identity is always path-plus-Git-revision; that
  source sections are stable anchors; that a new node type or frontmatter is
  available.
- **Requirement:** the bridge must support content-hash identity as a fallback
  for non-Git and external sources, tolerate heading and prose rewrites, remain
  prose-only unless evidence justifies structure, record unknown properties,
  and define rollback for restricted or read-only sources.

### `TAS-171-pilot-incremental-plan-intake`

- **Assumptions to audit:** that a representative corpus exists; that sources
  live in this repository; that pilots may mutate sources; that success
  thresholds are universal.
- **Requirement:** the pilot must accept synthetic, adapted, or volunteered
  sources, run read-only when permission is absent, treat success and failure
  thresholds as project-declared, and record which content never needed
  migration.

### `TAS-173-decide-plan-analyzer-surface` / `TAS-174-build-dry-run-plan-analyzer`

- **Assumptions to audit:** that analysis can read whole documents; that text
  sections exist; that Git is available; that classification is safe to act on.
- **Requirement:** the analyzer must default to deterministic and offline,
  abstain on unknown or unsupported properties, produce source-span citations
  and explicit uncertainty, stay read-only and preview-oriented, and never infer
  authoritative boundaries or adversarially convert unsupported formats.

### `TAS-175-decide-source-drift-policy` / `TAS-176-build-source-drift-reconciliation`

- **Assumptions to audit:** that sources are Git-tracked; that identity can be
  section-level; that drift is always semantic; that drift should block work.
- **Requirement:** drift detection must state the identity granularity, treat
  non-Git and restricted sources as supported or explicitly unsupported,
  distinguish formatting-only from semantic change, degrade unknown cases to a
  non-failing advisory, and never block execution without a project-declared
  policy.

### `TAS-177-decide-derived-plan-rendering` / `TAS-178-build-derived-plan-renderer`

- **Assumptions to audit:** that Markdown is the only format; that consumers are
  known; that a rendered plan may be an independent authority; that size is
  unbounded.
- **Requirement:** rendering must be one-way and explicitly derived, take format,
  storage, content, and size bounds as project-declared, and never become an
  independent owner of any mutable fact.

## Evaluation criteria

Braintree's model-level evaluation must separate costs that are comparable across
projects from costs that only the consuming project can set. Mixing them would
let a project-local threshold masquerade as a universal quality bar.

### General intake costs (comparable, model-level)

- **Admission correctness:** no node admitted without review; no mutable fact
  with two owners; no inferred entity persisted as truth.
- **Cold resumption:** a reader can resume admitted work without the source,
  the network, or hidden context.
- **Uncertainty transparency:** every unknown or unsupported property that
  affected a decision is recorded.
- **Review burden:** the number of reviewed decisions per admitted outcome.
- **Reconciliation correctness:** source changes are classified and applied per
  the declared policy, with formatting-only changes separable from semantic
  ones.
- **Decline fidelity:** unsupported work is declined explicitly with a reason,
  never approximated.

### Project-local measures (declared thresholds)

- **Discovery burden:** how much effort the project spends naming and exposing
  its sources and policies.
- **Source access:** latency, permission, credentialing, and availability.
- **Authority-conflict rate:** how often source and graph disagree in practice.
- **Dual-maintenance cost:** the cost of a permanent narrative-plus-graph split.
- **Retention and handling compliance:** whether the project's data rules are
  respected.
- **Integration friction:** hooks, CI, and tooling the project must maintain.

A project-local measure becomes a success criterion only when the project states
its threshold. The general measures are Braintree invariants and hold
regardless.

## Open questions deferred to downstream nodes

This model does not settle authority, identity, reconciliation cadence, or
capability surfaces; those belong to the decision and build nodes above. The
following remain explicitly open and must be answered with project input and
pilot evidence:

- The recommended default coexistence mode and its exceptions.
- Whether a bridge is prose-only or gains a command surface.
- Whether an analyzer, drift detector, or renderer are justified at all.
- The exact form of source identity when both Git and content hashes are absent.
- Which restricted-content handling rules Braintree can enforce versus only
  document.
