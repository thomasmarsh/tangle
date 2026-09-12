---
context_rev: 1
updated: 2026-09-12T23:35:42Z
summary: Has cumulative contract growth invalidated the compact-skill decision?
---

Area [[IDX-001-execution-graph]].

# Question

The compact-skill decision adopted a 13,481-byte `SKILL.md` after a measured 23.5% median token reduction. The current file is 28,282 bytes and 4,249 words. Which newer rules still belong in always-loaded prose, which can move behind direct commands or focused references, and what evaluation is needed before retaining the growth?

# Context

Area evidence: [[DEC-004-compact-skill-text]] requires future skill-text edits to preserve compactness and be evaluated with a matched token A/B. [[TAS-080-staged-token-ab]] is blocked on authorization for a separate direct-answer comparison and does not yet decide the cumulative contract-size question.

# Evidence

`git show 97e0848:SKILL.md | wc -c` reports 13,481 bytes; `wc -c SKILL.md` reports 28,282 bytes. `git diff --stat 97e0848..HEAD -- SKILL.md` reports 109 insertions and 26 deletions.
