---
context_rev: 1
priority: P2
updated: 2026-09-11T23:45:12Z
summary: Retarget installers, test runner, skill contract, and docs to the Python toolchain and delete tracked Ruby.
next: Update `scripts/install.sh` to install the Python entry points and metadata, then rewrite the Ruby test scripts.
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
