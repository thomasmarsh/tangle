---
context_rev: 1
priority: P1
updated: 2026-09-11T23:45:12Z
summary: Port the read-only vault validator to typed Python with identical checks, options, exit codes, and error strings.
next: Implement the validator module and convert `tests/graph-check.sh` assertions into pytest cases.
---

# Context

Parent [[TAS-037-port-ruby-implementation-to-typed-python]].

Depends on [[TAS-038-uv-scaffold-and-distribution-contract]] at context_rev 1.

Preserve `--allow-stale`, `--allow-orphan NODE`, `-h/--help`, exit codes 0/1/2, and the exact substrings the shell test greps for (`duplicate node identity:`, `broken link`, `unfinished task requires next`, `context_rev mismatch`, `invalid or missing context_rev pin`, `stored reciprocal edge`, `orphan unfinished node`, `parent cycle`).

# Outcome

A typed Python `graph-check` that enforces the same status-directory, frontmatter, lifecycle, canonical-edge, dependency-pin, reachability, cycle, and focus rules as `scripts/graph-check.rb`.

# Done when

Every expected failure in `tests/graph-check.sh` is reproduced (as pytest or an updated shell test) and all valid fixtures pass.
