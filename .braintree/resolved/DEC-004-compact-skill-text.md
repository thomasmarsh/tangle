---
context_rev: 1
updated: 2026-09-12T01:36:35Z
summary: Adopt the compact SKILL.md; a two-round A/B cut median benchmark tokens 23.5% by reducing repeated-context rounds.
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[TAS-020-token-benchmark]] at context_rev 6.

`SKILL.md` had grown to 22,183 B. The primary token benchmark copies the installed skill into an isolated fixture, so skill size is part of the measured context.

# Decision

Keep the `SKILL.md` contract text compact and adopt the tightened 13,481 B revision. Evaluate future skill-text edits with a two-round token A/B (`composite`, graph, small, 3 sessions per arm) and compare medians of total tokens, cached input, and model-invocation count, never a single run.

# Rationale

Compacting rationale, examples, and cross-section repetition shrank the file 39% (22,183 to 13,481 B) while preserving every `tests/test_skill.py` contract string and all operational rules.

Two independent rounds (3 live sessions per arm, `gpt-5.6-terra`/medium, CLI `0.154.0`) passed the exact-value gate in all 12 sessions. Combined n=6: median total 160,144 to 122,486 (-23.5%), median cached input 141,568 to 104,064 (-26.5%), median uncached plus output +12.1%. The tightened arm used fewer model invocations in both rounds (7 to 6, then 6 to 4) and about 23% less assistant narration.

Each round re-sends the conversation, so total tokens scale with model-invocation count and repeated-context size; a smaller skill compounds across rounds. The gain is fewer and cheaper repeated-context rounds, not less novel work.

# Consequences

- Adopted in commit `e2c620d`; evidence in `benchmark/token-ab*.json`.
- The fixture SHA-256 embeds the installed skill, so cross-skill comparisons are observational, not controlled. Ranges overlap at n=6: the direction is confirmed in both rounds, the magnitude is noisy.
- The recorder now waits for flushed session telemetry (`_wait_for_session_usage`, commit `95c1585`) after a concurrent run aborted on an unwritten session JSONL.
- Future edits must preserve the `tests/test_skill.py` contract strings or update that contract deliberately.
