---
context_rev: 1
priority: P2
updated: 2026-09-14T01:30:28Z
summary: Run the installed braintree command from the shared program's prepared environment so read-only commands need no uv cache.
next: Materialize the shared program environment in scripts/install.sh and exec it from the generated launcher.
---

# Context

Parent [[THO-025-round-nine-usage-feedback-analysis]].

Tangle `FBK-030` at `0.6.0+g169bad5`: the generated `<root>/.local/bin/braintree`
shim runs `uv run --project <program> --frozen braintree`, and `uv run`
initializes a writable cache before dispatching. In a sandbox that denies
`~/.cache/uv`, even `braintree help authoring` fails before rendering, so a
read-only command needs write access outside the repository. `scripts/install.sh`
copies the program tree but never materializes its environment, so the first
invocation also needs that cache to build the environment.

Reproduced: with `UV_CACHE_DIR` set to an unwritable directory, the installed
launcher fails with `Failed to initialize cache ... Permission denied` even when
`<program>/.venv` exists; `<program>/.venv/bin/braintree help authoring` with a
read-only `HOME` succeeds, so the prepared environment alone carries no cache
dependency.

# Outcome

Installing Braintree prepares the shared program's environment once, and the
generated launcher runs that environment directly, so no installed command —
read-only or not — initializes a uv cache. `uv run --frozen` remains only as the
fallback for a program whose environment is absent.

# Done when

- `scripts/install.sh` materializes `<program>/.venv` at install time with
  `uv sync --frozen`, adding the semantic extra only for `--semantic`.
- The generated launcher execs `<program>/.venv/bin/braintree` when it exists and
  otherwise falls back to the current `uv run --frozen` invocation, preserving
  the `--extra semantic` provider behavior.
- `tests/install.sh` proves the installed launcher renders `help` with a
  read-only `UV_CACHE_DIR`, and the semantic provider and no-op assertions still
  pass.
- `make test` passes.
