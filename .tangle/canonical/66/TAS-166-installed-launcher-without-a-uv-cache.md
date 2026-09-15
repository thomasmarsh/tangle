---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Run the installed tangle command from the shared program's prepared environment so read-only commands need no uv cache.
---

# Context

Parent [[THO-025-round-nine-usage-feedback-analysis]].

Hekate `FBK-030` at `0.6.0+g169bad5`: the generated `<root>/.local/bin/tangle`
shim runs `uv run --project <program> --frozen tangle`, and `uv run`
initializes a writable cache before dispatching. In a sandbox that denies
`~/.cache/uv`, even `tangle help authoring` fails before rendering, so a
read-only command needs write access outside the repository. `scripts/install.sh`
copies the program tree but never materializes its environment, so the first
invocation also needs that cache to build the environment.

Reproduced: with `UV_CACHE_DIR` set to an unwritable directory, the installed
launcher fails with `Failed to initialize cache ... Permission denied` even when
`<program>/.venv` exists; `<program>/.venv/bin/tangle help authoring` with a
read-only `HOME` succeeds, so the prepared environment alone carries no cache
dependency.

# Outcome

Installing Tangle prepares the shared program's environment once, and the
generated launcher runs that environment directly, so no installed command —
read-only or not — initializes a uv cache. `uv run --frozen` remains only as the
fallback for a program whose environment is absent.

# Done when

- `scripts/install.sh` materializes `<program>/.venv` at install time with
  `uv sync --frozen`, adding the semantic extra only for `--semantic`.
- The generated launcher execs `<program>/.venv/bin/tangle` when it exists and
  otherwise falls back to the current `uv run --frozen` invocation, preserving
  the `--extra semantic` provider behavior.
- `tests/install.sh` proves the installed launcher renders `help` with a
  read-only `UV_CACHE_DIR`, and the semantic provider and no-op assertions still
  pass.
- `make test` passes.

# Result

`scripts/install.sh` now materializes `<program>/.venv` with `uv sync --project
<program> --frozen` at install time, adding `--extra semantic` only for a
`--semantic` install, and the generated launcher execs
`<program>/.venv/bin/tangle` when it exists, falling back to the previous
`uv run --project <program> --frozen` invocation otherwise. The fallback keeps
the first run working before an environment exists and preserves the
`--extra semantic` provider default.

Evidence: a fresh `--codex --project` install produced a launcher that runs the
prepared environment directly, and `UV_CACHE_DIR=<unwritable> <launcher> help
authoring` rendered the authoring reference without touching uv, where the same
command previously failed at `Failed to initialize cache`. `tests/install.sh`
now exercises that read-only, cache-less path from `check_launcher` and stands
in a fake uv for both the install-time sync and the launcher fallback in the
semantic section. `make test` passes: ruff and strict mypy clean, `install tests:
passed`, `worktree-parallel` passed, and the pytest suite reported 720 passed, 3
skipped, 79 deselected. `tangle check` passed at 201 nodes.
