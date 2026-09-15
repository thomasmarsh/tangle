---
status: resolved
context_rev: 2
updated: 2026-09-14T23:40:13Z
summary: "Reject orientation-loop compaction: the recovered correct candidate used 157806 total tokens versus 118291 baseline."
---

# Context

Area [[IDX-001-execution-graph]].

# Result

The matched small graph baseline was correct at 118291 total tokens
(117062 input; 91904 cached; 1229 output). The candidate was also correctly
recorded at 157806 total tokens (156211 input; 127488 cached; 1595 output): it
is 39515 tokens higher. Its original recorder command exited 0, wrote
`benchmark/token-orientation-candidate-v2.json`, and its sole matching fresh
session has the matching fixture/skill hashes, model, effort, CLI version,
turn ID, exact JSON answer, and final cumulative snapshot. There was no
recording-pipeline failure to fix.

The prose edit remains reverted. Reject this orientation compaction; do not
retry the unchanged theory or spend another orientation candidate session.
