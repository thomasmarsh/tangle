---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: The uv package scaffold is green; installed skills run the `bt`/`graph-check` console scripts through `uv run`, not PEP 723 single files.
---

# Context

Parent [[TAS-037-port-ruby-implementation-to-typed-python]].

Open question this node settles: whether installed skill copies run a `uv`-managed package via console scripts or self-contained PEP 723 single-file scripts. The answer must keep the installer's copy-a-few-files model working and must not require a Ruby runtime.

# Outcome

A `uv`-managed project skeleton: `pyproject.toml` + `uv.lock`, a `src/braintree/` package with full annotations, and console entry points for `bt` and `graph-check`. Strict type checking (`mypy --strict`), Ruff, and pytest are configured in `pyproject.toml`; `make`-target wiring is deferred to [[TAS-042-retarget-installers-tests-docs-and-remove-ruby]].

# Decision

Installed skills run the `uv`-managed `braintree` package through its console scripts; do not ship PEP 723 single-file scripts.

- The package is the single source of truth. Entry points are `bt = "braintree.cli:main"` and `graph-check = "braintree.graph_check:main"`.
- An installed copy needs only `pyproject.toml`, `uv.lock`, `src/braintree/`, `SKILL.md`, and host metadata, and is invoked as `uv run --project <skill-dir> --frozen bt ...` or `... graph-check ...`.
- Runtime dependencies stay empty; prefer the standard library (`sqlite3`, `hashlib`, `subprocess`, `json`). No typed YAML parser is added now. If [[TAS-039-port-graph-check-validator-to-python]] cannot safely parse frontmatter with the stdlib, it must justify a typed YAML parser, which `uv run` resolves from the declared project dependency.
- Preserve the CLI contract in the scaffold: `bt` prints `0.1.0` for a sole `--version`/`-v`/`-V` and renders `--help` and errors as TOON fields; `graph-check` keeps `--allow-stale`, `--allow-orphan NODE`, `-h`/`--help`, and exit codes `0`/`1`/`2`. Command bodies remain stubs owned by TAS-039 and [[TAS-040-port-sqlite-sidecar-and-index-to-python]].

# Rationale

- One package avoids duplicating shared frontmatter, TOON, and sidecar helpers across five CLIs, which PEP 723 single-file scripts would force.
- `uv` is already the declared toolchain, and console scripts give the installer stable command names without a Ruby runtime.
- Empty runtime dependencies keep `uv sync` offline-friendly and installed skills small; the only plausible future dependency is a frontmatter parser, declared once.

# Consequences

- The installer must copy the package tree and run `uv`; [[TAS-042-retarget-installers-tests-docs-and-remove-ruby]] owns that change.
- PEP 723 is rejected, so standalone single-file execution is not a supported distribution path.
- This confirms the package/console-script assumptions the pinned consumers already record, so `context_rev` stays `1`.

# Evidence

- `uv sync` succeeds (14 packages resolved); `uv.lock` and `.python-version` pin Python `3.12`.
- `uv run bt --version` prints `0.1.0`; `uv run graph-check --help` prints the usage banner; `uv run bt --help` lists all ten commands.
- `uv run pytest` passes 8 scaffold tests; `uv run ruff check` passes; `uv run mypy` (strict) reports no issues in 5 source files.

# Done when

`uv sync` succeeds; `uv run bt --version`, `uv run graph-check --help`, `uv run pytest`, `uv run ruff check`, and strict type checking all pass on the scaffold; and the distribution/execution approach for installed skills is written down in this node or the README.

# Result

Re-confirmed after integration at `updated` time: `uv sync` resolved 14 packages; `uv run bt --version` printed `0.1.0`; `uv run graph-check --help` printed the usage banner; `uv run pytest` passed 8 tests; `uv run ruff check` and `uv run mypy` (strict, 5 source files) reported no issues. Distribution decision recorded under `# Decision`.
