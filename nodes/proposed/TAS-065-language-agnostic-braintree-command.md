---
context_rev: 1
priority: P2
updated: 2026-09-12T14:13:30Z
summary: Install a single `braintree` command into the home root's `.local/bin` and make it the only documented invocation, with no `uv`, Python, or implementation-language awareness in `SKILL.md` or consuming projects.
next: Add a language-agnostic `braintree` launcher, install it into the home root's `.local/bin`, and rewrite every documented invocation to use it.
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
