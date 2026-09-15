---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Announce a legacy-vault migration instead of relocating `nodes/` to `.tangle/` silently, and report the resolved vault path.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Hekate `FBK-015` finding 2 at `0.6.0+g4c6cafb`, re-checked at `c54728a` and
reproduced in [[THO-017-round-six-usage-feedback-analysis]]. Probe `/tmp/tangle-r6`:
from a root whose vault is the legacy `nodes/` directory (with
`nodes/index-map.md`), `tangle feedback record --route 'Area [[IDX-002-feedback]]' ...`
renamed `nodes/` to `.tangle/`, printed
`path: "/private/tmp/tangle-r6/.tangle/proposed/FBK-001-relocation-probe.md"`,
and printed no notice that a move had happened; a following `tangle migrate`
was a `no-op`. The relocation itself is now the decided behavior
([[DEC-008-vault-lives-under-dot-braintree]],
[[TAS-109-move-vault-to-dot-braintree]], `66556fa`), so the FBK's "never
relocate implicitly / refuse to write when the resolved vault differs" is
disposed; the demonstrated silence is not. `src/tangle/vault.py` performs
the rename inside `resolve()` and returns only the destination path, and
`src/tangle/feedback_record.py` prints `path` but never names a migration.

# Outcome

A command that migrates a legacy `nodes/` vault to `.tangle/` announces the
move in one line naming both paths, and its reported `path` names the resolved
vault directory, so an operator sees the relocation instead of discovering it
in the diff.

# Done when

- A command that migrates a legacy `nodes/` vault to `.tangle/` prints a one-line notice naming both the source and destination paths.
- The capture path's reported `path` names the resolved vault directory, so a migration that moved the vault is visible in the output.
- A behavior test in `tests/test_feedback_record.py` or `tests/test_vault.py` drives a legacy-vault root through the capture path and asserts the notice and the reported path.
- `make test` passes.

# Result

`src/tangle/vault.py` announces a migration the resolver performs:
`resolve()` renames a qualifying legacy `nodes/` vault through `migrate()` and
prints one line on stderr, `migrated vault: nodes -> .tangle`, naming the
source and destination directories relative to the vault root it read. The
notice never reaches stdout, so a command whose stdout is machine-readable TOON
stays parseable, and the resolved directory is still what `resolve()` returns,
so the capture path's reported `path` names `.tangle`. The rename stays
idempotent and silent when the vault is already migrated or the caller named the
directory with an operand or `TANGLE_NODES_DIR`.

Evidence: `tests/test_feedback_record.py::test_capture_announces_a_legacy_vault_migration`
drives the capture path from a legacy `nodes/` root in a temp dir with
`TANGLE_SIDECAR_DIR`/`TANGLE_PROJECT_ID` pinned inside it, and asserts the one-line
notice, the absence of `nodes/` afterwards, and a reported `path` under
`.tangle/proposed/`;
`tests/test_vault.py::test_resolve_announces_the_move_on_stderr_only` pins
stdout-cleanliness, the exact notice text, and silence on a second resolve of
the already-migrated vault. A scratch legacy-vault probe showed `node record`
and `feedback record` each printing the notice once on stderr, `frontier`
stdout staying `frontier[N]{id,status,...}` TOON, and the resolved `path`
naming `.tangle`. `make test` (ruff, mypy, 377 passed, 3 skipped, plus the
install and worktree-parallel screens) and `tangle check` pass.
