---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Make bare scripts/install.sh interactively discover and multi-select potential install targets instead of demanding explicit agent and destination flags.
---

# Context

Parent [[TAS-161-routine-interaction-zero-ceremony]].

`scripts/install.sh` requires `(--codex | --claude | --pi)` and `(--project DIR |
--home DIR)` on every invocation, so the caller must already know the agent and
the destination; `scripts/install-claude.sh` removes only the agent flag. Nothing
discovers candidate roots or offers a choice.

# Outcome

Running `scripts/install.sh` with no target arguments interactively presents the
potential install targets — detected project roots and home roots crossed with
the supported agents — as a multi-select and installs each selected target, while
the existing explicit flags remain for non-interactive and scripted use.

# Done when

- Bare `scripts/install.sh` presents a multi-select of discovered install
  targets.
- Selecting several targets installs each one.
- The existing explicit flags and `--dry-run` remain supported.
- Non-interactive invocation without a discoverable target fails clearly instead
  of hanging.
- Tests cover target discovery, the multi-select path, and the non-interactive
  path.
- `make test` passes.

# Result

Implemented in `scripts/install.sh`, which needed no companion file. A bare
invocation — no agent and no destination — now runs `interactive_select`: it
discovers the nearest enclosing project root by walking up from `$PWD` to the
first directory carrying a real project marker (`.git`, `pyproject.toml`,
`package.json`, `Cargo.toml`, `go.mod`), adds an existing `$HOME` that is not
that same root, crosses each root with `codex`, `claude`, and `pi`, prints the
numbered `targets[N]{index,agent,root,destination}` menu, and reads one line of
space- or comma-separated numbers; `all` selects every target and an empty line
cancels with `result: "cancelled"`. Each selected target runs the shared
`install_target` the explicit path also uses, so the skill prose, the one shared
per-root program with its install record, and the single launcher are still
written once per root by the existing copy-when-different logic and reported as
`outcomes[N]{agent,destination,program,launcher,result}`.

The explicit flag path is unchanged: parsing, `--dry-run`, `--semantic`, the
TOON fields, and the exit codes are byte-identical to the pre-change installer
for every flag-driven install and error path (old and new scripts diffed over
the flag, dry-run, semantic, version, and error paths; only `--help` changed, to
document the selector). Non-interactive stdin never
prompts and never hangs: a bare invocation whose stdin is not a terminal, or one
that discovers no target, exits 2 with a `stdin is not a terminal` /
`no install target was discovered` error and a flag-form help line.
`TANGLE_INSTALL_SELECTION` supplies the selection directly, the seam the tests drive
instead of a TTY.

Evidence: `tests/install.sh` adds a selector section — discovery of both roots
and all six crossed targets from the printed menu, a comma-separated `1,4`
selection installing exactly those two targets and their shared program and
launcher, a space-separated repeat reporting `no-op` for each, `all` installing
every target, an empty selection cancelling with nothing written, an interactive
`--dry-run` writing nothing, invalid and out-of-range selections failing, and a
non-terminal bare invocation failing with the explicit-flag error while a
flag-driven invocation with the same `</dev/null` stdin keeps installing without
a menu. `README.md` documents the interactive run and states that a
non-interactive run must name the flags; `AGENTS.md` keeps its explicit-flag
contract and adds that a bare run is terminal-only.

Limitations: the multi-select is driven through `TANGLE_INSTALL_SELECTION`, so the
line read from a real terminal (`read` after the menu) is the one uncovered
branch; selection is validated but not re-prompted, so a typo fails clearly
rather than looping. `scripts/install-claude.sh` still requires an explicit
destination, because the wrapper injects its own agent flag.

Gates: `tangle check` passed (197 nodes); `tangle benchmark verbs --verify`
passed; `make test` passed (719 passed, 3 skipped, 79 deselected). No benchmark
artifact was regenerated and no frozen source file was touched.
