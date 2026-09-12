---
context_rev: 1
priority: P2
updated: 2026-09-12T00:38:48Z
summary: Installers, tests, Makefile, and docs drive the uv-managed Python toolchain; all tracked Ruby is removed.
---

# Context

Parent [[TAS-037-port-ruby-implementation-to-typed-python]].

Depends on [[TAS-038-uv-scaffold-and-distribution-contract]] at context_rev 1.
Depends on [[TAS-039-port-graph-check-validator-to-python]] at context_rev 1.
Depends on [[TAS-040-port-sqlite-sidecar-and-index-to-python]] at context_rev 1.
Depends on [[TAS-041-port-benchmark-harnesses-to-python]] at context_rev 1.

Update `tests/install.sh` (it `cmp`s the Ruby files and invokes `ruby`), `tests/skill.sh` (Ruby assertions on `SKILL.md` that require `ruby scripts/graph-check.rb nodes`), `Makefile` targets, `README.md`, and the `SKILL.md` command references and integrity-command section. Remove `scripts/*.rb`, `tests/fixtures/fake-codex-mutation.rb`, and the Ruby test heredocs only after their Python replacements are verified. Preserve the installer's TOON output, `--version 0.3.1` behavior, and explicit-destination guarantees.

# Outcome

Installers, tests, Makefile, and docs drive the Python toolchain, and no tracked Ruby remains.

# Done when

`make test` and `git diff --check` pass with no tracked Ruby, and a `--dry-run` install still reports the correct destination without writing.

# Result

`scripts/install.sh` now copies the `uv` project into the skill destination: `SKILL.md`, optional `agents/openai.yaml`, `pyproject.toml`, `uv.lock`, `.python-version`, `README.md`, and `src/braintree/`. Installed copies run through `uv run --project <destination> --frozen bt|graph-check`, matching the distribution decision. `tests/install.sh` byte-compares the copied tree and runs the installed `graph-check`; `tests/skill.sh` became `tests/test_skill.py`; `tests/graph-check.sh` and `tests/worktree-parallel.sh` invoke the new Python `scripts/graph-check` launcher. `Makefile` runs pytest, ruff, strict mypy, and the shell suites, and `README.md`/`BENCHMARK.md`/`SKILL.md` name the Python commands. `token_benchmark.py` installs the package tree in its fixture and validates with `python -m braintree.graph_check`.

Evidence: `make test` passes (69 pytest tests, ruff, strict mypy, and every shell suite); `git ls-files` contains no `*.rb`; the token fixture `--check-fixture`/`--record` gates pass.
