---
context_rev: 1
priority: P2
updated: 2026-09-11T23:45:12Z
summary: Port the behavioral, storage, and token benchmark harnesses to typed Python with identical output and tracked-baseline verification.
next: Implement the behavioral and storage comparison harnesses, then the token benchmark and its fake Codex fixture.
---

# Context

Parent [[TAS-037-port-ruby-implementation-to-typed-python]].

Depends on [[TAS-038-uv-scaffold-and-distribution-contract]] at context_rev 1.

Preserve `--verify` baseline matching, the `filesystem_diagnostic{...}` and `storage{...}` output lines, the `--protocol`, `--check-fixture`, `--check-output-schema`, `--check-recording`, `--inspect-session`, and `--session` token-benchmark modes, the historical accounting output, and the fixture metadata hashes. Port `tests/fixtures/fake-codex-mutation.rb` so the mutation recorder test keeps its zero-live-call path.

# Outcome

Typed Python equivalents of `behavioral-benchmark`, `storage-comparison`, and `token-benchmark` that reproduce the tracked outputs and baselines.

# Done when

`tests/behavioral-benchmark.sh`, `tests/storage-comparison.sh`, and `tests/token-benchmark.sh` pass against the Python harnesses.
