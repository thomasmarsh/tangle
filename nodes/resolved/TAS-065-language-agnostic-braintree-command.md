---
context_rev: 1
priority: P2
updated: 2026-09-12T14:53:52Z
summary: Install a single `braintree` command into the home root's `.local/bin` and make it the only documented invocation, with no `uv`, Python, or implementation-language awareness in `SKILL.md` or consuming projects.
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[DEF-001-distribution-contract]] at context_rev 1.

Depends on [[DEC-005-reinstall-not-migration]] at context_rev 1.

Today every installed invocation names the implementation language and toolchain:
`uv run --project <skill-dir> --frozen bt ...` and `... graph-check ...`. That
leaks `uv`, the `pyproject.toml`/`uv.lock` layout, and Python into `SKILL.md` and
every consuming project. This node changes the documented CLI contract surface
named in [[DEC-005-reinstall-not-migration]], so its implementation is a MAJOR
contract change that carries the matching version bump.

# Outcome

Installation places an executable `braintree` command in the home root's
`.local/bin` (`~/.local/bin/braintree`), and that command is the single
documented entry point for every Braintree operation in every consuming
project. `SKILL.md`, `README.md`, and consuming projects reference only
`braintree`; none of them mention `uv`, Python, the skill's internal file
layout, or any implementation language.

# Done when

- `scripts/install.sh` installs an executable `braintree` command into
  `<home-root>/.local/bin` and reports it like the rest of the install output.
- The installed `braintree` command exposes the capabilities documented today
  under `bt`, `graph-check`, `feedback-scan`, and `feedback-record`, and runs
  from a consuming project root without the consumer knowing how it is
  implemented.
- `SKILL.md` contains no `uv run`, `--frozen`, `pyproject`, `uv.lock`, Python,
  or skill-directory path references; every documented invocation uses
  `braintree`.
- `README.md`, `AGENTS.md`, and the installer/`--help` text are likewise free of
  implementation-language awareness.
- The command's installation and a no-op reinstall are covered by
  `tests/install.sh`, and installation remains idempotent and testable against
  an explicit temporary home root per [[DEF-001-distribution-contract]].
- `make test` passes, including the `SKILL.md` contract assertions in
  `tests/test_skill.py`.

# Result

- `src/braintree/main.py` adds the unified `braintree` command and becomes the
  only declared console script; `python -m braintree` dispatches to it. `check`,
  `feedback scan`, `feedback record`, `benchmark token|behavioral|storage`, and
  the index and coordination verbs (`index`, `status`, `init`, `allocate`,
  `claim`, `release`, `search`, `backlinks`, `hash`, `stale`) are all reachable
  from the one command.
- `scripts/install.sh` generates `<root>/.local/bin/braintree` for every scope,
  reports it as `launcher:` in the install output, and leaves it untouched on a
  no-op reinstall. `tests/install.sh` runs the launcher's `--version` and a
  no-op reinstall against a temporary home root, per
  [[DEF-001-distribution-contract]].
- The seven per-command shell launchers and console scripts are gone; one
  `scripts/braintree` dev launcher replaces them, and `Makefile`,
  `tests/worktree-parallel.sh`, and the benchmark help text use the new command.
- `SKILL.md`, `README.md`, and `AGENTS.md` name only `braintree`.
  `tests/test_skill.py` asserts those documented surfaces contain none of
  `uv run`, `--frozen`, `pyproject`, `uv.lock`, `python`/`Python`, `.venv`, the
  internal console-script names, or the skill-directory layout.
- `pyproject.toml` moves `0.4.0` to `0.5.0`, the MAJOR contract-surface break
  named in [[DEC-005-reinstall-not-migration]].
- `make test` passes: ruff, mypy, the pytest suite, `tests/install.sh`, and
  `tests/worktree-parallel.sh`.
- The `nodes/index-map.md` Frontier recipe ends with `|| true`, so an empty
  frontier is a clean success; resolving the last unfinished node otherwise
  made the recipe exit non-zero.
