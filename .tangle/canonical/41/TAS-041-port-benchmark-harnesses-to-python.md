---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Port the behavioral, storage, and token benchmark harnesses to typed Python with identical output and tracked-baseline verification.
---

# Context

Parent [[TAS-037-port-ruby-implementation-to-typed-python]].

Depends on [[TAS-038-uv-scaffold-and-distribution-contract]] at context_rev 1.

Preserve `--verify` baseline matching, the `filesystem_diagnostic{...}` and `storage{...}` output lines, the `--protocol`, `--check-fixture`, `--check-output-schema`, `--check-recording`, `--inspect-session`, and `--session` token-benchmark modes, the historical accounting output, and the fixture metadata hashes. Port `tests/fixtures/fake-codex-mutation.rb` so the mutation recorder test keeps its zero-live-call path.

# Outcome

Typed Python equivalents of `behavioral-benchmark`, `storage-comparison`, and `token-benchmark` that reproduce the tracked outputs and baselines.

# Done when

`tests/behavioral-benchmark.sh`, `tests/storage-comparison.sh`, and `tests/token-benchmark.sh` pass against the Python harnesses.

# Result

`src/tangle/behavioral_benchmark.py`, `src/tangle/storage_comparison.py`, and `src/tangle/token_benchmark.py` replace the three Ruby harnesses; `tests/fixtures/fake-codex-mutation.py` replaces the Ruby fake; `scripts/behavioral-benchmark`, `scripts/storage-comparison`, and `scripts/token-benchmark` are thin Python launchers for the historical in-repo paths; and `pyproject.toml` declares the three new console scripts alongside `tangle` and `graph-check`.

Evidence: the three shell suites pass against the Python harnesses; `make test` passes; `uv run pytest` passes 61 tests including new `tests/test_behavioral_benchmark.py`, `tests/test_storage_comparison.py`, and `tests/test_token_benchmark.py`; `uv run ruff check` and strict `uv run mypy` are clean. Differential runs against the Ruby harnesses matched byte-for-byte: `--check-fixture` produced identical JSON for all four variants including `fixture_sha256`, the `--check-output-schema`/`--inspect-session`/`--check-recording`/`--session` outputs matched, and the fake-Codex `--record` mutation output matched after normalizing the temporary session path.

The token fixture still installs the Ruby `graph-check.rb` and invokes it for structural validation, preserving the historical fixture hashes; [[TAS-042-retarget-installers-tests-docs-and-remove-ruby]] owns replacing that installed content and deleting the Ruby sources.
