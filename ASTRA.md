# Tangle: improvements and direction

## Recommendation

Tangle should make resuming work cheap and dependable. Its strongest contribution
is the combination of readable execution memory, explicit next actions, and
checks that expose stale assumptions. Make that combination the product's center.

The next phase should consolidate the existing capabilities into a small,
coherent workflow. Shorten the skill, make the command assemble the context needed
to act, and provide a human view that explains how the pieces fit together.
Use those interactions to guide an incremental architectural rewrite.

This is a response to [NOTES.md](NOTES.md), informed by the current skill,
references, command implementation, installer, and test configuration. The
recommendations below are proposals for discussion, not adopted decisions or an
implementation backlog.

## What the current project reveals

Several concerns in the notes already have partial solutions:

| Concern | Current evidence | Remaining opportunity |
|---|---|---|
| Orientation overhead | `tangle packet` follows deliberate routes and returns `ready`, `blocked`, `ambiguous`, or `invalid`. | The skill still teaches agents to list frontier candidates and resolve them through coordinating parents. Make the precise answer the default entry point. |
| Repeated code exploration | `tangle manifest` exposes authored source paths, tests, verification gates, and compatibility constraints. | Include this information in the execution packet when present. |
| Human navigation | `views.py` generates disposable Markdown pages with summaries as link labels. | Extend these into explanations of an initiative, its decisions, and its remaining work. |
| Python and cache friction | The project already uses strict typed Python. Launchers prefer a prepared environment. | `Makefile` still invokes `uv run`; the fallback launcher does too. The development path still exposes cache permissions. |
| Expensive verification | Focused `make verify-<surface>` targets exist, and benchmark verification is separate. | Measure the remaining full-suite cost and distinguish everyday iteration from final acceptance. |

These findings matter because adding another command or another rule may deliver
less value than connecting what already exists.

The loaded [SKILL.md](SKILL.md) is 2,292 words and 15,511 bytes. Its contract test
allows 16,000 bytes. It is smaller than an earlier version, but an agent still
receives migration details, timestamp edge cases, decomposition rules, and
multi-writer handoff exceptions before doing ordinary work. The cost concern in
the notes is visible in the entry point itself.

## 1. Make the skill a small operating loop

Aim initially for roughly 400–700 words, as a design constraint to evaluate rather
than a claim about optimal token usage. Its job should be to tell an agent:

1. When durable execution memory is useful.
2. How to obtain the next authorized action and its required context.
3. How to record a meaningful result or a resumable stopping point.
4. Which check must pass before handing off graph changes.
5. Where to find instructions for conditional operations.

Keep the essential authority rules in this entry point: Markdown is canonical;
graph state does not confer user authorization; stale required context must be
reconciled; a task resolves only when its outcome is supported by evidence.

Move format details, migration procedures, clock handling, claim protocols, and
rare recovery cases into the relevant operation's help. Commands should stamp
timestamps, resolve identities, and validate transitions wherever possible. A
worker should need to understand what a semantic revision means, but should not
need to implement timestamp bookkeeping manually.

The distinction is between rules needed **before acting** and instructions needed
**when performing a particular operation**. A short skill remains safe only if
the latter appear at the point of use and the tooling catches structural errors.

Audit the prose tests at the same time. [tests/test_skill.py](tests/test_skill.py)
has useful behavioral tests, but also many exact sentence expectations. Preserve
literal checks for actual grammar; test other requirements through observable
behavior and working help routes. Otherwise each accumulated corrective sentence
becomes difficult to remove, even when the underlying behavior improves.

## 2. Finish the execution packet

The existing [packet command](src/tangle/packet.py) is the right foundation. It
already refuses to choose arbitrarily between multiple executable routes. Its
current output includes route evidence and dependency metadata, but its `files`
section contains only the task's own path; it does not assemble the manifest or
the task's full acceptance context.

Make the ordinary packet sufficient to start a bounded piece of work:

- The task, its next action, and completion criteria.
- The route that selected it, or the explicit assignment that scoped it.
- Required dependency revisions and readiness, with the context needed to use them.
- Known source and test locations, plus compatibility constraints.
- The expected verification and the operation for recording progress.

Support an explicitly assigned task or initiative as an input. Multiple
independent initiatives are legitimate; a global query may be ambiguous while a
scoped query has a clear answer. Report that distinction without silently turning
priority ranking into permission to work.

Reuse the existing manifest instead of inventing another planning format.
Prefer paths and symbols over brittle line numbers. Mark missing locations and
distinguish intended new files from stale references. These are starting points
for investigation, not a guarantee that the implementation cannot touch anything
else.

Bound the packet, but make omissions explicit. A shortened packet must identify
required material that remains unread. Avoid treating a dependency's matching
revision as proof that a fresh agent already knows its contents.

This provides a concrete response to orientation waste: move repeatable graph
traversal and context assembly into a deterministic operation, while retaining
the evidence behind its answer.

## 3. Give humans a composed document

Small nodes and readable overviews can coexist. Node boundaries should follow
durable outcomes and decisions; presentation can bring several nodes together.

Build on [the generated views](src/tangle/views.py) to offer an initiative page
that answers:

- What are we trying to achieve, and why?
- What approach have we chosen?
- Which decisions constrain it?
- What is complete, what remains, and what happens next?

The generated portions should link back to their sources and remain disposable.
Human-authored intent should have one canonical home. Avoid a hand-maintained
overview that copies task status and gradually disagrees with the graph.

The VISION → PLAN → task intuition is useful as a navigation structure. Start by
expressing it through existing Markdown and primary routes. Introduce new node
types only when they need distinct lifecycle or validation behavior. A vision
states the desired change and boundaries; a plan explains an approach; tasks own
verifiable outcomes. Dependencies and decisions still cross that hierarchy.

Keep individual nodes readable in full, but use length as a warning signal.
Splitting a coherent decision merely to satisfy a byte ceiling would increase
the very navigation cost we are trying to reduce.

## 4. Clarify what deserves memory

The current distinction between a durable outcome and an execution slice is
sound. Keep it. A large outcome can have a small next action without requiring a
new node for each working session.

I would refine the admission shortcut that work finished and committed in one
session needs no node. It is a useful default for routine implementation, but
session duration does not determine future value. A decision made in ten minutes
may constrain work for months, and a commit message may be a poor place to
rediscover it.

A compact admission rule could be:

> Keep unfinished executable state, decisions that constrain future work, and
> discoveries whose loss would cause meaningful repetition or error. Prefer
> updating the existing owner. Let Git carry routine implementation history.

Record at meaningful transitions: accepting an outcome, discovering a blocker,
changing a relied-upon assumption, or leaving work for later. Avoid mandatory
per-action logging. Helpful prompts at these transitions can improve consistency
without assuming an agent will proactively remember every bookkeeping rule.

Admission, semantic revision changes, and completion still require judgment.
The tool can require evidence or an explicit choice; it cannot determine that a
decision matters merely from valid syntax.

## 5. Separate workflow state from coordination

Support a single worker with minimal ceremony. Then add coordination capabilities
for the environments that need them:

| Environment | Coordination requirement |
|---|---|
| One worker | Read context, make the change, record the result, validate. |
| Multiple workers in one checkout | Exclusive ownership of overlapping write sets and serialized shared edits. Node ownership alone does not protect shared source files. |
| Separate local worktrees | Assignments tied to a base revision, local claims, and integration-time revalidation. |
| Separate hosts or infrequent integration | Durable proposals and explicit acceptance against current state; local leases cannot establish global ownership. |

Tangle already has extensive coordination and change-intake machinery. The goal
should be to make those capabilities optional and clearly bounded, with a common
assignment/result interface. An orchestrator can use that interface, and a single
agent can use the same basic execution packet directly.

The coordination reference currently says serial work also self-assigns a write
set and acquires a claim. Reconsider that requirement for an explicitly exclusive
session: coordination overhead should correspond to a concurrent-writer risk.

Keep claims separate from durable task status. Also distinguish a rebuildable
index from live lease state: losing an index costs time, while losing leases
removes evidence of ownership. Recovery must not assume that the loss proves no
worker remains active.

For helper-driven writes, validate the expected starting content before applying
changes. For integration, compare dependency context and completion evidence as
well as textual merge success. These checks make the concurrency contract
concrete without requiring one prescribed agent topology.

## 6. Keep repository authority; aggregate across projects

Default to a repository-local vault for work coupled to code. It allows a code
change, its decision context, and its task transition to travel together through
review and history.

A central location is useful for discovery and cross-project intent. Start with
a catalog that points to project authorities and generates combined views. Use
the existing project identity model to qualify references. Each record should
have one authoritative home.

If a team later needs independently versioned planning, support that explicitly,
including which code revision an assignment concerns. Moving the vault elsewhere
does not itself solve concurrency; it changes the synchronization problem.

## 7. Make identity and installation easy to use

Keep durable random identity internally. Restore human convenience through
display titles and command-level handles: a unique short prefix, an explicit
mnemonic alias, or a numbered selection from a displayed result. Resolve these
to canonical identity before writing persistent links. Ambiguous inputs should
return choices. A temporary result number must never become a durable reference.

The reported duplicate pi skill deserves a targeted diagnosis. I did not inspect
the user's installed skill directories, so the cause is unconfirmed. The
installer supports both home and project scopes; the product should explain
which copies an agent will discover and expose their paths and versions.

Add an installation diagnostic and explicit repair path. Installation should
prepare the runtime; ordinary command execution should use it directly. If that
runtime is missing, provide a clear repair instruction rather than unexpectedly
starting environment resolution inside a restricted session.

The cache issue is reproducible here: `make test` failed while opening
`~/.cache/uv/sdists-v9/.git`, before any test ran. The prepared-environment launcher
already addresses part of this problem, but the development commands need the
same treatment. No tests were subsequently run, per your instruction.

## 8. Rewrite around boundaries, incrementally

The project already has Python modules for storage, indexing, validation,
identity, and optional capabilities. The architectural task is to establish and
enforce their responsibilities, then simplify the implementation behind them.

Use a small dependency direction:

> Markdown parsing and typed graph model → queries and validation → explicit
> mutations → command and presentation adapters.

Keep search indexes and generated views replaceable. Put coordination behind a
separate interface. Semantic ranking, clustering, and research harnesses should
depend on the core without defining its everyday behavior.

Two concrete seams are worth addressing:

- `main.py` imports numerous benchmark and memory-evaluation modules alongside
  ordinary commands. Isolate development dispatch and load it only when requested.
- The packet and manifest modules explicitly explain that their placement avoids
  changing `cli.py`, because that file is frozen benchmark prompt content.
  Preserve such evidence in versioned fixture snapshots so production code can
  evolve without rewriting a historical measurement.

Treat a rewrite as a sequence of independently verifiable replacements that
preserve Markdown compatibility. Start with the execution packet and shared
graph interpretation. A new directory structure alone would not address the
agent's operating cost.

## 9. Evaluate cheaply before buying more agent runs

Do not spend on new live-agent benchmarks at this stage. Use offline scenarios
for correctness and deterministic cost indicators for regression detection:

- Does cold resumption select the intended action and expose its prerequisites?
- Does a stale decision prevent execution until reconciliation?
- Can a partial result be resumed without inventing new task boundaries?
- Does integration detect conflicting assumptions even after a clean text merge?
- Do commands work with a prepared runtime and an inaccessible package cache?

Measure entry-point size, packet bytes, required follow-up reads, command
latency, and test durations. These are engineering indicators; they do not prove
lower model token cost or better autonomous task completion.

Use ordinary development sessions as optional observational evidence of repeated
orientation and bookkeeping friction. Keep historical research artifacts, but
label historical operating contracts clearly: `BENCHMARK.md` still contains
status-directory guidance and statements about the absence of a database that
do not describe the current architecture.

## Suggested order

1. **Consolidate resumption.** Make `packet` the documented default, combine it
   with manifests and acceptance context, support scoped assignments, and shorten
   the skill. Acceptance: a fresh worker can identify the intended action and
   required reads without reconstructing the route manually.
2. **Remove everyday friction.** Diagnose duplicate installation, unify prepared
   runtime use, and add convenient identity resolution. Acceptance: common
   commands need neither hash transcription nor package-cache access.
3. **Improve human comprehension.** Compose initiative views over existing nodes
   and introduce vision/plan conventions. Acceptance: a reader can explain the
   goal, chosen approach, and current obstacle from one entry page.
4. **Extract the core.** Separate graph semantics, mutation, coordination, and
   research code while preserving observable behavior and Markdown compatibility.
5. **Revisit semantic features using concrete retrieval failures.** Clustering
   may help find duplication or neglected work, but it should follow improvements
   to explicit routes and document composition.

The central design test is simple: **does this feature reduce the amount an agent
or human must reconstruct before making the next correct change?** That gives
Tangle a clear direction and a practical reason to decline additional machinery.
