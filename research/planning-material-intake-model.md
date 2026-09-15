# Planning-material intake: variability and decision model

## Purpose and status

Planning material is any project-designated source used to inform future or
ongoing work: documents, tickets, notebooks, wikis, specifications, generated
plans, or other media. It may predate Tangle, coexist with admitted work, or
continue changing after related graph nodes exist.

This document is a research handoff for
`TAS-167-legacy-plan-intake-lifecycle`. It characterizes the decisions an intake
workflow must make; it is not itself a Tangle contract, source schema,
coexistence policy, or promise of tool support. `SKILL.md` remains authoritative
for graph admission, node boundaries, status, dependencies, and revisions. The
project remains authoritative for the meaning, access rules, and permitted use
of its source material.

The model deliberately does not select an authority mode, bridge shape,
analyzer, drift policy, or renderer. Those decisions belong to the downstream
nodes that can consider project choices and pilot evidence.

## Tangle-side constraints

These constraints follow from the current Tangle contract and apply when
planning material is used with Tangle:

1. A source-native unit is not automatically a graph unit. Headings, chunks,
   checkboxes, tickets, and extracted entities are evidence for review, not node
   boundaries.
2. Retrieval is not admission. Tools may locate or propose source evidence, but
   a reviewer applies the durable-outcome and update-existing rules before
   Markdown becomes authoritative graph state.
3. The vault is authoritative for Tangle graph state. That does not make it
   the authority for every project fact, requirement, narrative, or source.
4. Discoverability is not authorization or authority. Being able to read,
   parse, hash, or version a source says nothing by itself about whether the
   operation is permitted or whether the source governs a decision.
5. A degraded or partial observation must not be represented as complete or
   authoritative.
6. Admitted work must be resumable without hidden conversational context. Its
   declared resumption closure may include explicitly named, authorized sources
   or capabilities; the model does not assume the vault contains every source
   fact.

Two stronger propositions are hypotheses for later work, not settled
constraints: that every mutable project fact should have exactly one editable
owner, and that graph-derived views must always be one-way. `TAS-169` and the
pilot must define their scope and test their consequences.

## Nine variability axes

The axes are prompts for discovery, not enumerations of supported values. A
project may expose values not listed here, and a source may vary within one
axis by section, revision, reader, or operation.

### 1. Source discovery and identity

- How does the project designate a source as planning material?
- Where can it be addressed: repository path, external identifier, URL,
  project tool, generated output, or another mechanism?
- Which identity is stable enough for the intended operation: path, provider
  ID, revision, content digest, composite identity, or none?

Discovery and identity are related but distinct. Finding an object does not
establish that the same address identifies it across time.

### 2. Cardinality and relationships

- Are there zero, one, or many designated sources?
- Are they independent, overlapping, ordered, derived, superseding, or
  contradictory?
- Is completeness knowable, or can additional sources appear later?

### 3. Role and authority

- Is a source historical evidence, a living specification, rationale, an
  approval record, a backlog, a status surface, a derived view, or a mixture?
- Which statements, if any, may govern project action?
- Who can declare or change that authority, and at what granularity?

Role and authority cannot be inferred from age, location, structure, frequency
of editing, or confident prose.

### 4. Lifecycle and mutability

- Is the source immutable, append-only, rewritten, generated, branched,
  merged, renamed, archived, or deleted?
- Who or what edits it, and can edits occur concurrently with graph work?
- Which lifecycle events invalidate a prior observation or reference?

### 5. Format and structure

- Is the source text, structured data, a notebook, diagram, binary artifact,
  comment stream, or mixed media?
- Which structure is semantic and which is presentational?
- Can the available capability read it faithfully and cite stable evidence?

No format or section structure confers authority or defines graph boundaries.

### 6. Audience and access

- Who may discover metadata, read content, quote it, or act on it?
- Are access rights reader-specific, time-limited, credentialed, audited, or
  unavailable to an agent?
- Does successful access now imply anything about future resumption access?

### 7. Handling and retention

- May content be copied into the vault, summarized, hashed, cached, logged, or
  sent to an optional provider?
- Must the source remain in place or be retained for a defined period?
- What redaction, residency, deletion, or audit obligations apply?

Read-only access is not sufficient permission to copy, quote, hash, or transmit
content.

### 8. Integrations

- Which tools read or write the source: Git, CI, issue trackers, generators,
  chat systems, LLM pipelines, or bespoke services?
- Which integration side effects, availability assumptions, and failure modes
  matter to intake?
- Is there an explicit capability for the operation, and what fidelity does it
  promise?

### 9. Project-specific semantics

- What do project terms such as owner, approved, done, blocked, requirement,
  or plan mean?
- Which project events or roles can settle ambiguity?
- Which compatibility obligations constrain changes to existing workflows?

Tangle must not redefine these meanings merely to normalize an input.

## Classifying an intake decision

The labels *universal*, *project-declared*, *discoverable*, *unknown*, and
*unsupported* are useful, but they are not five mutually exclusive classes of
a source property. They answer different questions:

| Label | Dimension | Question answered | Consequence |
| --- | --- | --- | --- |
| **Tangle-fixed** (universal) | Governing rule | Does the current Tangle contract already constrain this operation? | Apply the contract; do not ask a project to override it. |
| **Project-declared** | Decision authority | Must an authorized project role choose the policy, meaning, or permission? | Obtain and cite that decision before relying on it. |
| **Discoverable** | Evidence method | Can a named capability observe the fact with stated scope and fidelity? | Record the observation and its limits; do not turn evidence into policy. |
| **Unknown** | Current knowledge | Is a relevant answer unresolved, unavailable, or not yet observed? | Decide whether it matters to the proposed operation; do not invent it. |
| **Unsupported** | Capability relation | Can the chosen capability faithfully perform the requested operation on this input? | Decline that operation or use an explicitly approved alternative. |

The unit of classification is a question about a proposed operation, not an
entire document. For example, Git tracking can be discovered, permission to
store excerpts is project-declared, the current completeness of a remote read
may be unknown, and section-level citation may be unsupported by the selected
reader. All four can be true simultaneously.

Project declarations and observations also need evidence. A declaration may be
stored in project policy; an observation should name its capability, target,
scope, version or time when relevant, and limitations. Confidence from an LLM
is an observation about a model output, not proof of the source fact it asserts.

## Operation gate and safe behavior

Before an intake operation, answer only the questions material to that
operation:

1. **Purpose:** What decision or action will the operation support?
2. **Contract:** Which Tangle rules constrain the result?
3. **Authority:** Who may authorize the access, handling, policy, and mutation?
4. **Evidence:** What has actually been observed, at what scope and fidelity?
5. **Support:** Can the selected capability perform this operation faithfully?
6. **Admission:** If graph state may change, who will review the proposed
   outcome and boundary?

Then use the narrowest justified branch:

- If an unknown is irrelevant to the operation, leave it unresolved. Do not
  manufacture durable bookkeeping for every conceivable property.
- If an unknown is material but the operation remains authorized and useful,
  proceed with an explicit limitation and preserve only the evidence needed for
  later review.
- If permission, authority, or fidelity is material and unresolved, defer that
  operation or decline it. A read-only operation is not automatically safe.
- If a capability is unsupported, describe the unsupported operation and
  input. Do not label the whole source unsupported when another faithful,
  authorized adapter or manual review may exist.
- If a reviewer admits or updates graph state, record enough decision context
  and evidence lineage to resume the outcome. An inference may be adopted after
  review; it must not masquerade as a source assertion.

Never infer any of the following merely from observable source characteristics:

- authority from existence, age, location, version control, or prose style;
- permission from technical accessibility;
- completeness from a successful or large read;
- node boundaries from layout, chunks, embeddings, or extracted entities;
- semantic equivalence from matching headings or formatting-only diffs;
- a safe storage or transmission policy from the absence of a restriction;
- approval to mutate, annotate, freeze, archive, or delete a source.

### Provenance and resumption

Evidence provenance and decision rationale are complementary, not substitutes.
Where material, an intake result should make it possible to reconstruct:

- which source object and observed version or state supplied evidence;
- what span or scope was actually reviewed and what was omitted;
- which capability or person produced the observation;
- which reviewer accepted, rejected, or transformed it into graph state; and
- which declared sources or capabilities a future reader still needs.

The bridge decision may choose the durable representation. This model requires
the information to be sufficient for the claimed resumption and audit behavior;
it does not mandate frontmatter, a node type, a path-plus-revision identity, or
a content hash.

## Content cues and failure modes

The following are review cues, not a document schema or a disposition mapping:

- rationale and history;
- prospective outcomes, requirements, and acceptance criteria;
- decisions or definitions that may affect consumers;
- mutable status, next actions, blockers, or dependencies;
- speculation and alternatives;
- completion claims and supporting evidence; and
- contradictions, duplicated assertions, or stale references.

Common hazards include partial access, restricted content, unstable anchors,
generated churn, conflicting sources, stale checklists, lossy conversion,
oversized inputs, and source deletion. The same cue may be ignored, cited,
retained in the source, used to update an existing node, or support a new node
after review. Its label alone does not decide the disposition.

## Scenario matrix

These scenarios test whether the model exposes the right decision points. The
“next probe” is conditional on authorization and capability; it is not a
predetermined coexistence mode.

| ID | Given conditions | Material unknowns | Narrow next probe | Invalid inference to catch |
| --- | --- | --- | --- | --- |
| S1 | Immutable in-repository Markdown; project declares it historical | Whether it is complete or still relevant | Record observable identity and review only evidence needed for the selected outcome | Historical does not mean complete or correct |
| S2 | Git-tracked living spec repeatedly rewritten by an LLM | Section authority, storage permission, stable anchors | Ask the project to identify governing content; test citations across a rewrite | Git history does not select hybrid mode or authority |
| S3 | Planning material spans a wiki, tracker, and notebooks with partial access | Corpus completeness, cross-source precedence, quote permission | Inventory only permitted metadata and surface missing coverage | A reachable source is not the whole corpus |
| S4 | The project designates no planning material | None for intake | Use ordinary Tangle planning and admission | Intake machinery is not required |
| S5 | A plan is regenerated during builds | Generator inputs, edit policy, authority of output | Observe generation behavior and ask which surface, if any, governs | Generated does not automatically mean non-authoritative |
| S6 | A living plan contradicts its checklist and current graph state | Which assertion governs and whether the conflict itself should be admitted | Cite the conflict at verified versions and request review | Ambiguity does not require rejecting every possible node |
| S7 | A credentialed remote source has no Git revision | Permission to read, hash, store, and revisit; provider identity guarantees | Use only provider metadata or content operations the policy allows | Non-Git does not imply that content hashing is permitted or sufficient |
| S8 | A binary or deeply nested source lacks a faithful installed reader | Whether an authorized adapter or human export exists | Decline the attempted parse and name the missing fidelity | One unsupported parser does not make the source globally unsupported |

The matrix should grow from pilot counterexamples. Synthetic cases can test
safety and classification logic; volunteered real cases are needed before
claiming representativeness or maintenance benefits.

## Downstream handoff

The model constrains assumptions that downstream work must avoid. It does not
choose those nodes' outcomes.

### `TAS-169-settle-plan-graph-authority`

- Do not infer authority from source form or observed behavior.
- Define the granularity of any “one editable owner” rule and distinguish
  Tangle graph state from other project facts.
- Decide, rather than assume, the supported coexistence modes, default,
  exceptions, write-back behavior, and transition events.

### `TAS-170-define-plan-bridge-contract`

- Do not presume Git, stable paths, stable sections, content-hash permission, or
  one source per bridge.
- Define identity, reviewed scope, limitations, decision lineage, remaining
  source dependencies, reconciliation state, completion, and rollback only to
  the degree needed for demonstrated resumption.
- Keep the first representation prose-only or add structure based on evidence,
  not this model.

### `TAS-171-pilot-incremental-plan-intake`

- Select cases across materially different axes and state their authorization
  boundaries before reading or mutating sources.
- Predeclare tasks, baselines, measures, and failure criteria. Synthetic cases
  test known hazards but cannot establish external validity alone.
- Record when graph-only resumption succeeds and when a declared source or
  capability remains part of the resumption closure.

### `TAS-172-codify-plan-intake-workflow`

- Promote only constraints supported by the settled decisions and pilot
  evidence.
- Preserve the difference between current contract, recommended default,
  project option, capability limitation, and unresolved question.

### `TAS-173` / `TAS-174` — analyzer decision and implementation

- Do not assume whole-document access, stable text spans, Git, or permission to
  transmit content.
- Make proposals auditable and visibly non-authoritative; represent partial
  reads, uncertainty, and abstention.
- Let the decision node choose deterministic, model-assisted, hybrid, or no
  analyzer from measured pilot costs.

### `TAS-175` / `TAS-176` — drift decision and implementation

- Define drift relative to a selected identity, observed states, and the
  authority policy; do not equate every byte change with semantic drift.
- Specify behavior for missing access, unstable anchors, non-Git sources, and
  uncertain classifications.
- Let the decision node choose cadence and enforcement. This model does not
  require a non-failing advisory or authorize a blocker.

### `TAS-177` / `TAS-178` — rendering decision and implementation

- Name the consumer and task that a derived view would serve before selecting
  format, content, storage, ordering, or size bounds.
- Test whether the view improves that task and whether users mistake it for an
  editable authority.
- Let the decision node dispose the branch when exact graph queries are enough.

## Evaluation design

Evaluation has three layers that should not be collapsed into one list of
“universal” costs.

### Contract and safety checks

These are pass/fail properties of the intake behavior:

- source-native structure does not create or size nodes automatically;
- partial or degraded reads are labeled with their scope;
- source access, copying, transmission, and mutation stay within declared
  authorization;
- graph mutations receive review and pass ordinary Tangle validation; and
- an unsupported operation is reported without a lossy result being presented
  as faithful.

### Empirical pilot measures

Each measure needs a denominator, collection method, and baseline:

- **Resumption success:** completion rate on predeclared cold-reader tasks,
  separately for graph-only and declared-source-available conditions.
- **Resumption cost:** elapsed time, tool calls, bytes or tokens read, and
  source or node opens per successful task.
- **Review yield:** accepted updates or admitted outcomes per proposal reviewed,
  with rejection reasons.
- **Duplicate-owner incidence:** conflicting editable claims found per admitted
  outcome, including conflicts created by the workflow.
- **Conflict detection:** precision and recall on seeded contradictions, plus
  reviewed findings on real cases where recall is unknowable.
- **Reconciliation burden:** review time and edits per material source change,
  separated from formatting-only churn.
- **Provenance auditability:** sampled decisions that another reviewer can trace
  to the evidence and review action claimed.
- **Abstention quality:** unsafe operations correctly declined and supported,
  authorized operations unnecessarily declined.

Tokens, files, and time are costs, not evidence of correctness on their own.
“Cold resumption” must name what the cold reader is allowed to access.

### Project acceptance thresholds

The project chooses acceptable accuracy, latency, privacy, maintenance,
authority-conflict, and integration-cost thresholds for its deployment. A
pilot may propose thresholds, but must label them as hypotheses until an
authorized project role accepts them.

## Open decisions

The following remain deliberately unsettled:

- the recommended coexistence mode and whether permanent hybrid operation is
  supported;
- the scope and granularity of a one-owner authority rule;
- whether a durable bridge is needed and how it identifies and cites sources;
- whether resumption should ever require source access;
- which pilot population is representative of intended users;
- whether analyzer, drift, or renderer capabilities earn their complexity;
- which reconciliation events warn, block, or require explicit disposition;
  and
- which handling rules Tangle can enforce rather than merely document.
