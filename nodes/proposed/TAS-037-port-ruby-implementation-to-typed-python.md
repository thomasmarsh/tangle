---
context_rev: 1
priority: P1
updated: 2026-09-11T23:45:12Z
summary: Replace the Ruby Braintree implementation with a fully typed uv-managed Python project while preserving command behavior and Markdown authority.
next: Resolve [[TAS-038-uv-scaffold-and-distribution-contract]].
---

# Context

Area [[IDX-001-execution-graph]].

The current implementation is Ruby plus POSIX shell: `scripts/bt`, `scripts/bt-index.rb`, `scripts/graph-check.rb`, the three benchmark scripts, the installers, and Ruby test scripts. Command names, arguments, TOON-style output, exit codes, and Markdown/sidecar authority must stay behaviorally identical; only the implementation language, typing, and toolchain change. Runtime should prefer the Python standard library (`sqlite3`, `hashlib`, `subprocess`, `json`) so installed skills stay self-contained.

# Outcome

A clean, fully typed Python project managed by `uv` that provides the `bt` sidecar/query CLI, the `graph-check` vault validator, the benchmark harnesses, and the install/test tooling, with no tracked Ruby remaining.

# Done when

`make test` passes against the Python implementation; no tracked `*.rb` or Ruby test code remains; the installers place working Python tooling into Codex and Claude skill destinations; and `SKILL.md`/`README.md` name the Python commands.
