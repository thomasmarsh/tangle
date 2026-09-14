---
context_rev: 1
updated: 2026-09-14T18:52:20Z
summary: Define the opt-in change-intake protocol v1.
---

Parent [[TAS-192-deliver-opt-in-parallel-graph-mutation-and]].

# Context

The design starts from `research/parallel-graph-mutation-and-reconciliation.md` and must preserve its pay-for-what-you-use boundary. Parent routing is supplied by decomposition.

The first release serves multiple clients contributing graph mutations in one working directory. Repository-bearing worktree contributions are the next compatibility layer; cross-host coordination is deferred.

# Invariant

A versioned change-intake contract defines one normalized internal model without requiring ordinary single-writer agents to author proposals, footprints, receipts, or integration decisions. Direct Markdown remains canonical and is the default mutation path.

# Done when

- The definition names the exact escalation triggers for direct editing, assigned-write-set coordination, local proposal intake, and worktree reconciliation.
- `braintree-change/v1` specifies its canonical byte encoding and digest domain; globally unique proposal identity; optional non-authoritative actor and run metadata; base witness retention; local symbols; supported operations; derived read/write footprints; preconditions; and deterministic error codes.
- The local MVP explicitly states which graph-only operations and `repository_effect: none` transitions it accepts, which task resolutions it must reject or defer because repository effects cannot be proven, and how later worktree payloads add exact commit, tree, or patch binding.
- Submission sealing and storage immutability, pending-set semantics, superseding drafts, exact-equivalence absorption, ambiguity decisions, dispositions, acceptance records, receipts, retry recovery, and retention ownership are specified.
- The acceptance boundary states what is atomic in one working directory, how current Git and node hashes are rechecked, when permanent IDs and host timestamps materialize, and what happens when the head or a precondition moves.
- Compatibility and versioning rules preserve ordinary node commands and the existing read-only `braintree reconcile` view.
- The definition allocates detailed protocol prose to a conditional reference and per-command help, leaving only a compact escalation route in `SKILL.md`.
- Contract fixtures cover canonicalization, corruption, unsupported operations, absent actor metadata, stale bases, and downgrade or unknown-version rejection.
