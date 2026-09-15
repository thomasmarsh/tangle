---
status: resolved
context_rev: 2
updated: 2026-09-15T00:48:52Z
summary: The vault lives under .tangle/ and a legacy nodes/ vault is migrated in place.
---

Area [[IDX-001-execution-graph]].

Depends on [[DEC-005-reinstall-not-migration]] at context_rev 2.

# Context

Every Tangle command and every consumer instruction named the vault directory `nodes/`. The owner directed that the vault tree live under a hidden `.tangle/` directory instead, so the graph directory does not collide with a project's own `nodes/` content and reads as tool state.

# Decision

The vault is the `.tangle/` directory: `.tangle/index-map.md` plus the fixed status directories `.tangle/proposed/`, `.tangle/active/`, `.tangle/blocked/`, and `.tangle/resolved/`. `tangle` resolves that directory from the current project root by default; `TANGLE_NODES_DIR` and an explicit `NODES`/`--nodes` operand still override it and are never migrated. The directory name changed from `.braintree/` to `.tangle/` in the tangle rebrand; the location and migration rules are otherwise unchanged.

A project that still holds `nodes/index-map.md` and no `.tangle/` is migrated in place by a one-time rename to `.tangle/`. `tangle migrate [ROOT]` performs and reports the rewrite, and the default vault resolver performs the same rename automatically so an upgrade needs no manual step. The portable id-reservation markers that the old layout nested at `nodes/.tangle/reservations` are merged to `.tangle/reservations`.

# Rationale

A hidden, single-purpose directory is unambiguous: it cannot be confused with a project's own `nodes/` source tree, and the default resolution is one rule. DEC-005 requires a dedicated decision before any migration ships; this is that decision. Automatic detection is safe here because the trigger is narrow and one-way: it fires only when a legacy `nodes/` vault exists and no `.tangle/` does, and the rename is idempotent and leaves the Markdown bytes unchanged.

# Consequences

The vault Markdown format changes incompatibly: the fixed status-directory path now includes `.tangle/`, so an older installed skill that reads `nodes/` will not find the vault. Per [[DEC-003-semantic-versioning]] this is a MAJOR change and bumps the version in the same change. `.gitignore` ignores only `.tangle/reservations/` and `.tangle/.obsidian/`, so the vault itself stays tracked. `tangle feedback scan` reads either layout without migrating an external vault. Recovery is the consumer's Git history; validation is `tangle check` and `tangle index` passing on the migrated vault.
