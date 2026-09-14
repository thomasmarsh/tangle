---
context_rev: 1
priority: P0
updated: 2026-09-14T19:35:47Z
summary: Implement stable lowercase node and project identity.
next: Implement the stable store, identity grammar, and compatibility migration.
---

Parent [[TAS-193-same-directory-graph-contribution-intake]].

# Context

Gated on [[DEF-003-opt-in-change-intake-protocol-v1]].

This task separates logical identity, project authority, canonical location, content revision, and presentation before proposal encoding depends on any of them. Existing uppercase numeric nodes are legacy inputs, not a reason to preserve centralized numeric allocation for new nodes.

Gates my artifacts enter: `tests/test_scaffold.py` and `tests/install.sh` for packaged source or reference files, `tests/test_skill.py` for contract text, the graph and vault tests for format discovery, and the default ruff, mypy, and pytest discovery over new modules.

# Outcome

Every newly admitted node has a lowercase globally collision-resistant identity and a stable canonical path under a clone-stable project UID, while existing vaults and uppercase numeric references remain readable through an explicit migration and compatibility contract.

# Done when

- A random immutable project UID is committed with the vault and shared by clones. It is explicitly distinct from the existing Git-common-directory hash used to locate same-host sidecar state.
- Lowercase project aliases use a conservative ASCII grammar, live in presentation or local registry state, and never confer authority. CLI input accepts `tas-...` locally and `tangle:tas-...` as a qualified convenience spelling, then resolves the latter to the committed project UID.
- New `tas`, `tho`, `def`, `idx`, and `fbk` IDs are assigned only at admission from a documented 96-bit-or-stronger collision-resistant construction. Proposal-local symbols remain noncanonical, content hashes remain revision witnesses, and no shared numeric sequence is needed for new identities.
- Newly stored identifiers, filenames, project aliases, and qualified reference components use lowercase ASCII. Input normalization and duplicate checks cannot let differently cased spellings become distinct on a case-sensitive filesystem or alias on a case-insensitive one.
- Canonical nodes occupy one stable, optionally sharded path derived from immutable identity, with an immutable creation label only if the format retains one for readability. Status becomes an authoritative node field rather than part of the path.
- Same-project graph edges remain valid Obsidian wikilinks. Cross-project edges use a distinct durable Braintree reference or URI containing the immutable project UID; a colon-qualified shorthand is never stored as though it were a local wikilink. Missing project registration preserves a visible unresolved external edge.
- Legacy uppercase numeric IDs, basenames, wikilinks, and status-directory nodes remain readable during a versioned compatibility window. Migration is one-way, collision-checked, recoverable, and uses an intermediate path for case-only renames. It preserves Git history as far as Git can detect and rewrites canonical backlinks coherently.
- The stationary-storage benchmark is rerun under the derived-index architecture and measures stable paths, status transitions, direct point edits, sidecar loss, Obsidian navigation, case behavior, and optional symlink views. The selected layout and rejected alternatives are recorded with rollback evidence.
- Tests cover clone-stable project identity, alias collision and rename, local and qualified resolution, ID collision injection, content edits without identity changes, case-insensitive equivalence, mixed legacy/new vaults, interrupted migration, and round-trip Markdown preservation. `braintree check`, `make test`, and the storage benchmark gate pass.
