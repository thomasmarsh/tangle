---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Move the vault to .braintree/ with automatic legacy migration across code, docs, tests, and this
---

Area [[IDX-001-execution-graph]].

Depends on [[DEC-008-vault-lives-under-dot-braintree]] at context_rev 1.

# Outcome

Every Braintree command reads the vault at `.braintree/` by default, a legacy `nodes/index-map.md` vault is detected and migrated in place, and no surface still instructs an agent to read or write `nodes/`.

# Done when

- The default vault directory is `.braintree` in every command, with `BT_NODES_DIR` and explicit operands unchanged.
- A `nodes/index-map.md` vault with no `.braintree/` is migrated by `braintree migrate [ROOT]` and by the default resolver.
- `AGENTS.md`, `SKILL.md`, `references/`, `README.md`, `index-map.md`, and per-verb help name `.braintree`.
- This repository's vault lives at `.braintree/`, `.gitignore` keeps the vault tracked, and the test suite pins the new default and migration.
- `make test` passes.

# Result

The vault is `.braintree/` and a legacy `nodes/` vault is migrated in place.

- `src/braintree/vault.py` owns resolution: `default_directory`, `legacy_directory`, `migrate` (with the nested reservation merge), and `resolve`. `resolve` returns an explicit operand or `BT_NODES_DIR` unchanged and migrates only the default `nodes/index-map.md` when `root/.braintree` is absent.
- `braintree migrate [ROOT]` reports `migrated` or `no-op`; the default resolver, `check`, `index`, `node record`, and `feedback record` migrate automatically. `feedback scan` reads `.braintree/` or legacy `nodes/` without migrating an external vault, and reservations moved from `nodes/.braintree/reservations` to `.braintree/reservations`.
- `SKILL.md`, `AGENTS.md`, `references/`, `README.md`, `BENCHMARK.md`, `.braintree/index-map.md`, and per-verb help name `.braintree`; `.gitignore` ignores only `.braintree/reservations/` and `.braintree/.obsidian/`. The migration commit also tracked the five `.braintree/.obsidian/` workspace files, so the ignore rule never applied; they were removed from tracking with `git rm -r --cached` while staying on disk.
- This repository's vault moved to `.braintree/`. `.braintree/resolved/DEC-008-vault-lives-under-dot-braintree.md` records the decision, [[DEC-005-reinstall-not-migration]] was amended to `context_rev 2`, and its pin in [[TAS-065-language-agnostic-braintree-command]] was reconciled.
- `pyproject.toml` moved `0.5.0` to `0.6.0`, the MAJOR vault-format change [[DEC-003-semantic-versioning]] requires.

Evidence: `tests/test_vault.py` pins legacy detection, the reservation merge, idempotency, explicit and configured overrides, the `migrate` command outcomes, and default-resolver migration through `check`; `tests/test_bt_foundation.py` and `tests/test_bt_reconcile.py` exercise `.braintree`; `braintree check` and `make test` pass.
