---
status: resolved
context_rev: 1
updated: 2026-09-15T02:47:49Z
summary: Improve Tangle workflow efficiency.
---

Area [[IDX-001-execution-graph]].

# Outcome

Reduce the token, orientation, and verification cost of routine Tangle work without weakening graph correctness or final acceptance.

# Done when

- The direct children are resolved or deliberately disposed.
- Their evidence is rolled up into a measurable workflow-efficiency result.

# Result

All six direct children are resolved and their evidence rolled up:

- Scoped-verification gate speedup: `make verify-<surface>` runs lint, type, `tangle check`, and only the focused tests mapped to a surface; `make verify-check` measured 6.1 s warm / 27 s cold against 110.8 s for `make test` (about 18x faster), and a deliberate mapped defect failed the scoped gate while the broad graph check stayed green.
- Storage-agnostic test-fixture abstraction: `tests/vault_helpers.py` exposes `canonical_path`/`write_node`, `iter_nodes`/`find_node`/`find_nodes`/`find_typed`, and `deterministic_id`/`fixed_identity`, so capture, feedback, decomposition, and installer tests assert identity and CLI output through helpers rather than layout or numeric-filename assumptions.
- Frontier execution-manifest read surface: a strict `# Manifest` body section (source, test, verify, compat) is authored intent and resolved read-only by `tangle manifest NODE`, which reports missing or malformed entries and never writes back.
- Strict work-packet read surface: `tangle packet` follows index, hub, and coordinating `next` routes to return the sole executable frontier node with readiness, pinned-dependency, parent-route, files, and verification metadata, or a structured blocked/ambiguous result.
- Skill hot-path reduction: `SKILL.md` dropped from 15,867 to 15,511 bytes while every pinned rule stayed in the core and conditional detail routed to help topics.
- Migration-milestone convention: cross-cutting compatibility migrations expose an ordered set of independently acceptable milestones, so a broad migration task's `next` never leaves the first implementation slice ambiguous.
