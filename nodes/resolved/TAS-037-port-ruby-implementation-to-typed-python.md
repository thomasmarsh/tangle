---
context_rev: 1
priority: P1
updated: 2026-09-12T00:38:48Z
summary: The Ruby implementation is fully replaced by a typed uv-managed Python project; no tracked Ruby remains.
---

# Context

Area [[IDX-001-execution-graph]].

The current implementation is Ruby plus POSIX shell: `scripts/bt`, `scripts/bt-index.rb`, `scripts/graph-check.rb`, the three benchmark scripts, the installers, and Ruby test scripts. Command names, arguments, TOON-style output, exit codes, and Markdown/sidecar authority must stay behaviorally identical; only the implementation language, typing, and toolchain change. Runtime should prefer the Python standard library (`sqlite3`, `hashlib`, `subprocess`, `json`) so installed skills stay self-contained.

# Outcome

A clean, fully typed Python project managed by `uv` that provides the `bt` sidecar/query CLI, the `graph-check` vault validator, the benchmark harnesses, and the install/test tooling, with no tracked Ruby remaining.

# Done when

`make test` passes against the Python implementation; no tracked `*.rb` or Ruby test code remains; the installers place working Python tooling into Codex and Claude skill destinations; and `SKILL.md`/`README.md` name the Python commands.

# Result

`src/braintree` provides `bt`, `graph-check`, and the three benchmark harnesses; `pyproject.toml`/`uv.lock` are the distribution; the installers copy the `uv` project into Codex and Claude skill destinations and installed copies run through `uv run --frozen`; the tests, `Makefile`, `SKILL.md`, and `README.md` name the Python commands. All five children (TAS-038 through TAS-042) are resolved.

Evidence: `make test` passes with 69 pytest tests, ruff, and strict mypy; `git ls-files` contains no `*.rb`; `tests/install.sh` runs the installed `graph-check` from both agent destinations.
