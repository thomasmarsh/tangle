---
context_rev: 4
updated: 2026-09-14T20:01:50Z
summary: Define the opt-in change-intake protocol v1.
---

Parent [[TAS-192-deliver-opt-in-parallel-graph-mutation-and]].

# Context

The design starts from `research/parallel-graph-mutation-and-reconciliation.md` and must preserve its pay-for-what-you-use boundary. Parent routing is supplied by decomposition.

The first release serves multiple clients contributing graph mutations in one working directory. Before proposal intake, it establishes stable lowercase node and project identity, a stationary canonical store, automatic full-store hash reconciliation, and project-owned Markdown projections. Repository-bearing worktree contributions are the next compatibility layer; cross-host coordination is deferred.

# Invariant

A versioned change-intake contract defines one normalized internal model without requiring ordinary single-writer agents to author proposals, footprints, receipts, integration decisions, indexes, aliases, or status views. Direct Markdown remains canonical and is the default mutation path; Braintree owns every derived projection.

# Done when

- The definition names the exact escalation triggers for direct editing, assigned-write-set coordination, local proposal intake, and worktree reconciliation.
- The definition separates immutable logical node identity, content hashes, stable canonical paths, project authority, project aliases, abbreviations, and human-facing projections. New node IDs use a type prefix plus exactly 128 bits encoded as 26 lowercase Crockford Base32 characters with canonical payload grammar `[0-7][0-9a-hjkmnp-tv-z]{25}`; legacy uppercase numeric IDs remain readable through an explicit migration window.
- A committed cryptographically random project UID uses the same 128-bit lowercase Crockford Base32 payload with a `prj-` prefix, remains stable across clones, and is distinct from the same-host sidecar key. Unqualified node references mean the current project, `alias:node` is input and display shorthand, and durable cross-project references expand aliases to the project UID through a grammar that does not masquerade as a local wikilink.
- Compact human terminal views may show a type prefix plus at least eight payload characters and an explicit ellipsis, lengthening deterministically until unique in the rendered result set. Full canonical IDs remain available in a full-width terminal mode and mandatory in canonical or durable artifacts and structured or machine-readable output; abbreviations never become accepted or stored identities and require no client-managed index.
- The stable-store format makes status authoritative in node content rather than path and states whether an immutable creation label remains in the basename. Content hashes identify exact bytes and optimistic preconditions, never mutable logical identity.
- Every project-scoped command that reads or mutates graph state performs a complete exact-byte hash census of canonical nodes before answering, reconciles new, changed, and vanished files into the derived index transactionally, and makes no client maintain changed-path hints. Mutation commands publish their known post-write delta without a redundant second census; global help, version, and installation operations remain vault-independent.
- Braintree generates deterministic disposable Markdown pages for status, area, priority, recent, and registered external-project views using canonical summaries as link display text. Views and optional symlinks are excluded from discovery and authority, and their absence or corruption cannot hide a canonical node.
- `braintree-change/v1` specifies its canonical byte encoding and digest domain; globally unique proposal identity; optional non-authoritative actor and run metadata; base witness retention; local symbols; supported operations; derived read/write footprints; preconditions; and deterministic error codes.
- The local MVP explicitly states which graph-only operations and `repository_effect: none` transitions it accepts, which task resolutions it must reject or defer because repository effects cannot be proven, and how later worktree payloads add exact commit, tree, or patch binding.
- Submission sealing and storage immutability, pending-set semantics, superseding drafts, exact-equivalence absorption, ambiguity decisions, dispositions, acceptance records, receipts, retry recovery, and retention ownership are specified.
- The acceptance boundary states what is atomic in one working directory, how the universal census and operation preconditions are rechecked, when collision-resistant permanent IDs and host timestamps materialize, how projections follow acceptance, and what happens when the head or a precondition moves.
- Compatibility and versioning rules preserve ordinary node commands and the existing read-only `braintree reconcile` view.
- The definition allocates detailed protocol prose to a conditional reference and per-command help, leaving only a compact escalation route in `SKILL.md`.
- Contract fixtures cover casing and identity canonicalization, clone-stable project scope, local and qualified reference resolution, direct edits with preserved metadata, projection recovery, corruption, unsupported operations, absent actor metadata, stale bases, and downgrade or unknown-version rejection.

# Result

Resolved `braintree-change/v1` in `references/change-intake.md`: it defines the
opt-in escalation boundary, canonical envelope and digest, identity/reference
grammar, census and projections, graph-only MVP boundary, reconciliation and
semantic decisions, serialized acceptance and receipt recovery, retention, and
the compatibility surface. `TAS-203` owns stable identity/store implementation;
`TAS-204` owns universal census/projection implementation; `TAS-195` through
`TAS-198` own local proposal commands and verification; `TAS-199` through
`TAS-202` own the bound-worktree extension. The help topic exposes the reference
without imposing it on ordinary direct Markdown work.
