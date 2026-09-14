---
status: proposed
context_rev: 2
updated: 2026-09-14T23:40:13Z
summary: How should living planning documents coexist with or migrate into the execution graph?
---

Area [[IDX-001-execution-graph]].

# Question

How should Braintree coexist with large, organically evolved planning documents, including projects that want gradual migration, permanent hybrid use, or full conversion, without creating two competing sources of truth?

# Context

The current contract explains detailed planning after work is represented as nodes: a user-requested plan may pre-create proposed children, while ordinary decomposition is just in time and outcome-based. It does not define an intake lifecycle for a pre-existing living plan whose narrative, rationale, history, checklists, and execution state have been repeatedly rewritten by LLMs. [[THO-002-fit-for-purpose-assessment]] judged recursive planning a strong fit, but did not settle coexistence or migration. [[THO-024-whether-node-files-need-a-bounded-load-band-with]] concerns node load size, not authority across a graph and a source plan.

`research/rag-perspective-evaluation.md` identifies Braintree as governed,
versioned execution memory rather than general-document GraphRAG. It recommends
keeping repository documents directly observable, refusing automatic entity
graph extraction and broad model summaries as authority, and admitting only a
selective, current, source-backed evidence closure for action. A legacy plan is
therefore source material at the intake boundary, not automatically a set of
nodes and not automatically project truth merely because it is long-lived.

# Hypothesis

Default to a staged hybrid bridge, not wholesale conversion. Explicitly classify
the source plan as one of: an immutable historical snapshot, an authoritative
living narrative/specification, or a temporary migration source. In every mode,
Braintree becomes authoritative for admitted execution state, dependencies,
decisions that consumers must pin, and the current frontier. Give every fact one
owner; represent the plan with a routed bridge node that names the source path,
its authority class, and reconciliation state; extract reviewed, outcome-shaped
nodes just in time; and retire status/checklist editing in the plan once its
corresponding work enters the graph. Full migration is an explicit terminal
mode, while a permanent narrative-spec plus execution-graph split is valid.

# Test

- Define coexistence modes and the authority boundary for narrative, decisions, acceptance criteria, status, dependencies, and history.
- Distinguish source retrieval from admission: source sections may be found or
  cited automatically, but node creation and boundaries remain reviewed and
  outcome-based.
- Define how a bridge records source identity and detects meaningful source drift without copying the whole plan into the vault.
- Define incremental extraction, full migration, reconciliation, rollback, and completion/archival behavior.
- Test the protocol on a large organically edited plan containing contradictions, completed work, speculative branches, embedded decisions, and stale checklists.
- Decide whether an advisory import command is justified; any command should preview mappings and never infer authoritative node boundaries without review.
