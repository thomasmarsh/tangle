---
context_rev: 2
priority: P1
updated: 2026-09-10T21:19:50Z
summary: Prior behavioral evidence is limited to deterministic filesystem diagnostics, not model-token benchmarking.
---

# Context

Area [[IDX-001-execution-graph]].

# Outcome

Verify that the hardening work delivers actionable-only, long-lived execution memory and bounded, reproducible real-work evidence; repair any concrete integration defects.

# Done when

Implementation, fixtures, documentation, installation, graph invariants, and requested verification commands have been audited and evidenced.

# Result

Audited TAS-009 through TAS-017 against the semantic-revision, canonical-edge,
reachability, decomposition, decision-memory, admission, graph-check,
behavioral-benchmark, and status-authority outcomes. Repaired the behavioral
fixture so its cold-resume P0 item is active with an executable next action,
made workflow assertions validate selected records rather than output wording,
and made orphan discovery target unfinished work. Added the fixture index route
to match the claimed resumption path and updated deterministic baselines.

Repaired copied-index storage comparison state so each Git scenario reads its
checked-out index instead of inheriting a mutable in-memory array. `make test`,
`make benchmark`, `make storage-comparison`, a 10,000-node behavioral run,
graph checking, installer tests, Ruby syntax checks, and whitespace checking
all pass. The remaining limits are documented: broad graph questions still
require bounded linear scans. The audit's behavioral and storage evidence
measures deterministic local file work only; [[TAS-020-token-benchmark]]
establishes the separate actual-token objective.
