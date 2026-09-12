---
context_rev: 1
priority: P1
updated: 2026-09-12T00:10:42Z
summary: Port the read-only vault validator to typed Python with identical checks, options, exit codes, and error strings.
---

# Context

Parent [[TAS-037-port-ruby-implementation-to-typed-python]].

Depends on [[TAS-038-uv-scaffold-and-distribution-contract]] at context_rev 1.

Preserve `--allow-stale`, `--allow-orphan NODE`, `-h/--help`, exit codes 0/1/2, and the exact substrings the shell test greps for (`duplicate node identity:`, `broken link`, `unfinished task requires next`, `context_rev mismatch`, `invalid or missing context_rev pin`, `stored reciprocal edge`, `orphan unfinished node`, `parent cycle`).

# Outcome

A typed Python `graph-check` that enforces the same status-directory, frontmatter, lifecycle, canonical-edge, dependency-pin, reachability, cycle, and focus rules as `scripts/graph-check.rb`.

# Done when

Every expected failure in `tests/graph-check.sh` is reproduced (as pytest or an updated shell test) and all valid fixtures pass.

# Result

`src/braintree/graph_check.py` replaces the scaffold stub with the full validator; the stdlib flat-frontmatter parser avoids a runtime YAML dependency. `tests/test_graph_check.py` ports every `tests/graph-check.sh` fixture and failure to pytest (23 tests pass) and covers `--allow-stale`, `--allow-orphan`, and the `-h/--help`/exit-code surface. Differential runs against `scripts/graph-check.rb` matched byte-for-byte on 27 fixture variants (all shell mutations plus resolved-next, bad frontmatter, root/non-IDX, index table/link, focus, multi-route, and frontier cases). `uv run ruff check`, `uv run mypy` (strict), and `make test` pass.
