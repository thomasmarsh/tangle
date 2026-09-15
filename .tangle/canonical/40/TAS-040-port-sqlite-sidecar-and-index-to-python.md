---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Port the `tangle` sidecar, Markdown index builder, and FTS/claim/allocation logic to typed Python with unchanged output and semantics.
---

# Context

Parent [[TAS-037-port-ruby-implementation-to-typed-python]].

Depends on [[TAS-038-uv-scaffold-and-distribution-contract]] at context_rev 1.

The Python port replaces the shell `scripts/tangle` wrapper and `scripts/tangle-index.rb`. Keep the Git-common-dir project identity (`sha256` first 20 hex), external sidecar location (`$XDG_STATE_HOME/tangle` fallback `~/.local/state/tangle`), WAL mode, positive-lease claims, atomic `BEGIN IMMEDIATE` allocation, the `df`-based network-filesystem guard, and the exact TOON field output. Use the stdlib `sqlite3` module (verify FTS5 availability) instead of shelling out to `sqlite3`. Note the current hazard that a fresh sidecar's `id_sequences` does not reconcile with existing Markdown IDs; decide whether `reindex` should seed sequences to avoid collisions.

# Outcome

A typed Python `tangle` with the same ten commands, output, and error/help messages, backed by a rebuildable SQLite derived index and same-host coordination state.

# Done when

`tests/tangle-foundation.sh`, `tests/tangle-index.sh`, and `tests/tangle-verification.sh` pass against the Python `tangle`, including contention, expiry, recovery after database loss, cross-worktree identity, and network-guard refusal.

# Result

`src/tangle/sidecar.py` owns project identity, the external sidecar path, the `df` network guard, WAL schema init, and atomic `BEGIN IMMEDIATE` allocation/claims; `src/tangle/index.py` ports the frontmatter scan, `nodes`/`edges`/FTS rebuild, search, backlinks, and stale queries; `src/tangle/cli.py` implements all ten commands with the scaffold's TOON surface, and `src/tangle/__main__.py` enables `python -m tangle`. `scripts/tangle` is now a thin launcher for the Python package, so the three existing shell suites exercise the port unchanged.

Evidence: `make test` passes with `scripts/tangle` running Python (foundation, index, and verification). `uv run pytest` passes 38 tests, including new `tests/test_tangle_foundation.py`, `tests/test_tangle_index.py`, and `tests/test_tangle_verification.py` that reproduce the shell scripts' contention, dense concurrent allocation, expiry, base-hash mismatch, Markdown immutability during reindex, database-loss recovery, cross-worktree identity, and network-guard refusal. Differential runs against the former Ruby/shell implementation matched byte-for-byte on reindex/search/backlinks/stale and every coordination success and error path (only expected `tangle` vs `scripts/tangle` help-text and sidecar-path differences). `uv run ruff check` and `uv run mypy` (strict, 13 files) are clean.

ID-sequence seeding was kept identical to the Ruby behavior to preserve semantics: a fresh sidecar still starts sequences empty, so the pre-existing allocation-versus-Markdown collision hazard is unchanged and remains orthogonal to this port. `scripts/tangle-index.rb` is left in place, unused, for [[TAS-042-retarget-installers-tests-docs-and-remove-ruby]] to delete.
