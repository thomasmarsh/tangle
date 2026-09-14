---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: The vault lives under .braintree/ and a legacy nodes/ vault is migrated in place.
---

Area [[IDX-001-execution-graph]].

Depends on [[DEC-005-reinstall-not-migration]] at context_rev 2.

# Context

Every Braintree command and every consumer instruction named the vault directory `nodes/`. The owner directed that the vault tree live under a hidden `.braintree/` directory instead, so the graph directory does not collide with a project's own `nodes/` content and reads as tool state.

# Decision

The vault is the `.braintree/` directory: `.braintree/index-map.md` plus the fixed status directories `.braintree/proposed/`, `.braintree/active/`, `.braintree/blocked/`, and `.braintree/resolved/`. `braintree` resolves that directory from the current project root by default; `BT_NODES_DIR` and an explicit `NODES`/`--nodes` operand still override it and are never migrated.

A project that still holds `nodes/index-map.md` and no `.braintree/` is migrated in place by a one-time rename to `.braintree/`. `braintree migrate [ROOT]` performs and reports the rewrite, and the default vault resolver performs the same rename automatically so an upgrade needs no manual step. The portable id-reservation markers that the old layout nested at `nodes/.braintree/reservations` are merged to `.braintree/reservations`.

# Rationale

A hidden, single-purpose directory is unambiguous: it cannot be confused with a project's own `nodes/` source tree, and the default resolution is one rule. DEC-005 requires a dedicated decision before any migration ships; this is that decision. Automatic detection is safe here because the trigger is narrow and one-way: it fires only when a legacy `nodes/` vault exists and no `.braintree/` does, and the rename is idempotent and leaves the Markdown bytes unchanged.

# Consequences

The vault Markdown format changes incompatibly: the fixed status-directory path now includes `.braintree/`, so an older installed skill that reads `nodes/` will not find the vault. Per [[DEC-003-semantic-versioning]] this is a MAJOR change and bumps the version in the same change. `.gitignore` ignores only `.braintree/reservations/` and `.braintree/.obsidian/`, so the vault itself stays tracked. `braintree feedback scan` reads either layout without migrating an external vault. Recovery is the consumer's Git history; validation is `braintree check` and `braintree index` passing on the migrated vault.
