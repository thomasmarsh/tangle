---
status: proposed
context_rev: 2
priority: P0
updated: 2026-09-14T23:40:13Z
summary: Implement immutable local change submission and inspection.
next: Implement the v1 local proposal codec, store, and CLI commands.
---

Parent [[TAS-193-same-directory-graph-contribution-intake]].

# Context

Gated on [[TAS-204-full-census-indexing-markdown-views]].

This task implements only the same-directory, graph-only intake slice defined by v1. Submission begins after the universal hash census has reconciled direct edits, uses the stable lowercase project and node reference model, must not modify canonical nodes while a client submits or inspects a proposal, and must fail closed on unsupported repository-bearing operations.

# Outcome

A client can submit one immutable graph contribution through an intent-level CLI and later inspect it by stable proposal identity without authoring envelope boilerplate or touching canonical graph state.

# Done when

- A focused change-intake module owns canonical encoding, domain-separated digest verification, proposal identity, operation parsing, derived footprints, base witnesses, and non-clobbering local storage.
- `braintree change submit`, `change pending`, and `change inspect` expose the contract with stable TOON and machine-readable forms; exact syntax follows the resolved definition and appears in per-command help.
- Submission derives lowercase proposal ID, project UID, timestamp, hashes, expected node state, expected absence, normalized local or qualified references, and mechanical read/write footprints whenever the operation supplies enough information; optional producer and run IDs remain opaque and never affect acceptance.
- Sealing uses exclusive creation, verifies bytes after writing, rejects replacement or digest mismatch, and treats pending proposals as an unordered set. A revision creates a new proposal linked by `supersedes_proposal`.
- The store remains explicitly non-authoritative and no command in this task edits a canonical node, authoritative status field or legacy path, shared manifest, acceptance record, receipt, Git ref, or Git index.
- Unknown versions, malformed operations, lost base witnesses, path traversal, symlink escape, unsupported repository effects, and concurrent same-name submissions fail deterministically without a partial sealed object.
- Unit and multi-process tests cover identical, colliding, malformed, anonymous, and concurrently submitted proposals. The relevant fast gates pass.
