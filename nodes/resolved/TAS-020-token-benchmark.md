---
context_rev: 6
priority: P1
updated: 2026-09-11T01:59:04Z
summary: Corrects historical and live token accounting for cumulative per-turn snapshots.
---

# Context

Area [[IDX-001-execution-graph]].

# Outcome

Measure actual Codex/model token consumption from fresh controlled sessions;
do not use file reads, bytes, or work units as an optimization metric.

# Result

`scripts/token-benchmark.rb` generates fixed small/large graph and conventional
plan fixtures in isolated Git repositories. The graph fixture copies the exact
repository skill distribution (`SKILL.md`, Codex `agents/openai.yaml`, and
checker) to the installed project-skill path, explicitly invokes it, records
its SHA-256, and is structurally valid except for its one deliberate orphan
and two named stale dependency pins. Opt-in fresh `codex exec -C` sessions use a strict output schema,
ignore unrelated user config/rules, and verify recorded CLI version, model,
reasoning effort, and fixture cwd from safe session telemetry fields. Zero-token
tests verify fixtures, graph structure, and sanitized telemetry parsing. No
live baseline is present or claimed.

Historical session logs for benchmark-development tasks contain token telemetry,
but they are multi-turn implementation/audit work rather than fresh matched
fixture runs, so they are not benchmark samples. Keep the baseline absent until
the opt-in protocol records correct graph and plan sessions.

Historical import derives a single safe task path, CLI version, model, and
reasoning effort from session telemetry (or rejects absent/ambiguous values).
Caller-supplied settings can only validate those observations. It requires a
nonempty turn ID for each accepted usage record, rejects malformed or regressing
cumulative snapshots, and sums only each distinct turn's final snapshot.

The corrected historical totals are 1,631,517 for
`/root/token_benchmark_realism` and 1,758,454 for
`/root/token_fixture_audit`; both are implementation cost only.
