---
status: resolved
context_rev: 1
updated: 2026-09-15T00:48:52Z
summary: Move the vault to .tangle/ with automatic legacy migration across code, docs, tests, and this
---

Area [[IDX-001-execution-graph]].

Depends on [[DEC-008-vault-lives-under-dot-braintree]] at context_rev 2.

# Outcome

Every Tangle command reads the vault at `.tangle/` by default, a legacy `nodes/index-map.md` vault is detected and migrated in place, and no surface still instructs an agent to read or write `nodes/`.

# Done when

- The default vault directory is `.tangle` in every command, with `TANGLE_NODES_DIR` and explicit operands unchanged.
- A `nodes/index-map.md` vault with no `.tangle/` is migrated by `tangle migrate [ROOT]` and by the default resolver.
- `AGENTS.md`, `SKILL.md`, `references/`, `README.md`, `index-map.md`, and per-verb help name `.tangle`.
- This repository's vault lives at `.tangle/`, `.gitignore` keeps the vault tracked, and the test suite pins the new default and migration.
- `make test` passes.

# Result

The vault is `.tangle/` and a legacy `nodes/` vault is migrated in place.

- `src/tangle/vault.py` owns resolution: `default_directory`, `legacy_directory`, `migrate` (with the nested reservation merge), and `resolve`. `resolve` returns an explicit operand or `TANGLE_NODES_DIR` unchanged and migrates only the default `nodes/index-map.md` when `root/.tangle` is absent.
- `tangle migrate [ROOT]` reports `migrated` or `no-op`; the default resolver, `check`, `index`, `node record`, and `feedback record` migrate automatically. `feedback scan` reads `.tangle/` or legacy `nodes/` without migrating an external vault, and reservations moved from `nodes/.tangle/reservations` to `.tangle/reservations`.
- `SKILL.md`, `AGENTS.md`, `references/`, `README.md`, `BENCHMARK.md`, `.tangle/index-map.md`, and per-verb help name `.tangle`; `.gitignore` ignores only `.tangle/reservations/` and `.tangle/.obsidian/`. The migration commit also tracked the five `.tangle/.obsidian/` workspace files, so the ignore rule never applied; they were removed from tracking with `git rm -r --cached` while staying on disk.
- This repository's vault moved to `.tangle/`. `.tangle/resolved/DEC-008-vault-lives-under-dot-braintree.md` records the decision, [[DEC-005-reinstall-not-migration]] was amended to `context_rev 2`, and its pin in [[TAS-065-language-agnostic-braintree-command]] was reconciled.
- `pyproject.toml` moved `0.5.0` to `0.6.0`, the MAJOR vault-format change [[DEC-003-semantic-versioning]] requires.

Evidence: `tests/test_vault.py` pins legacy detection, the reservation merge, idempotency, explicit and configured overrides, the `migrate` command outcomes, and default-resolver migration through `check`; `tests/test_tangle_foundation.py` and `tests/test_tangle_reconcile.py` exercise `.tangle`; `tangle check` and `make test` pass.
