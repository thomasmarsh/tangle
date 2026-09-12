---
context_rev: 1
priority: P1
updated: 2026-09-11T23:45:12Z
summary: Port the `bt` sidecar, Markdown index builder, and FTS/claim/allocation logic to typed Python with unchanged output and semantics.
next: Implement sidecar modules for project identity, network guard, schema init, claims, allocation, and index/search/backlinks/stale commands.
---

# Context

Parent [[TAS-037-port-ruby-implementation-to-typed-python]].

Depends on [[TAS-038-uv-scaffold-and-distribution-contract]] at context_rev 1.

The Python port replaces the shell `scripts/bt` wrapper and `scripts/bt-index.rb`. Keep the Git-common-dir project identity (`sha256` first 20 hex), external sidecar location (`$XDG_STATE_HOME/braintree` fallback `~/.local/state/braintree`), WAL mode, positive-lease claims, atomic `BEGIN IMMEDIATE` allocation, the `df`-based network-filesystem guard, and the exact TOON field output. Use the stdlib `sqlite3` module (verify FTS5 availability) instead of shelling out to `sqlite3`. Note the current hazard that a fresh sidecar's `id_sequences` does not reconcile with existing Markdown IDs; decide whether `reindex` should seed sequences to avoid collisions.

# Outcome

A typed Python `bt` with the same ten commands, output, and error/help messages, backed by a rebuildable SQLite derived index and same-host coordination state.

# Done when

`tests/bt-foundation.sh`, `tests/bt-index.sh`, and `tests/bt-verification.sh` pass against the Python `bt`, including contention, expiry, recovery after database loss, cross-worktree identity, and network-guard refusal.
