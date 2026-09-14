---
context_rev: 2
priority: P0
updated: 2026-09-14T19:35:47Z
summary: Build read-only local proposal reconciliation planning.
next: Extend reconciliation over the immutable local pending set.
---

Parent [[TAS-193-same-directory-graph-contribution-intake]].

# Context

Gated on [[TAS-195-immutable-local-change-submission]].

Reuse the graph parsing, dependency verdicts, full-census index, and existing Git-ref reconciliation primitives rather than creating a second interpretation of Braintree nodes. Reconciliation is a pure plan over sealed proposals and the canonical snapshot produced after the command hashes every stored node.

# Outcome

An integrator can deterministically discover which local proposals are exact duplicates, mechanically compatible, stale, overlapping, or semantically unknown before any canonical file changes.

# Done when

- Collection verifies proposal digests and retained bases, ignores arrival order, consults existing terminal evidence, and distinguishes malformed, recovery, pending, and superseded submissions.
- Exact operation or result equivalence keeps every origin and marks duplicates for absorption without allocating more than one canonical identity.
- A deterministic overlap graph covers canonical targets, authoritative status fields and legacy paths, parent `next`, dependency producer/consumer interaction, local symbols, derived read/write paths, expected absence, and declared graph predicates.
- Classification includes at least apparently-disjoint, commutes, same-result, needs-rebase, stale-context, same-node-overlap, frontier-contention, identity-collision, possible-redundancy, semantic-conflict, boundary-change, and unknown. Only mechanically proven cases advance automatically.
- The planner materializes symbolic IDs and a noncanonical timestamp in a scratch vault, runs the same full-census index and projection derivation over that candidate, runs plain `braintree check`, recomputes stale consumers against the combined candidate, and proves order independence before reporting `commutes`.
- Semantic similarity may nominate review but never proves independence, consolidation, or a node boundary. An uncertain clean textual replay remains `needs-revision` or `unknown`.
- Output has stable component, action, reason, proposal, target, and failed-precondition codes suitable for both shell and orchestrator callers, while the existing `braintree reconcile --base/--head` surface remains compatible.
- Tests permute submission order and cover exact duplicates, disjoint creation, same-node amendments, parent contention, dependency drift, cycles, invalid unions, and split-versus-amend ambiguity. No test observes a canonical mutation.
