---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Correct the Codex skill destination and AXI behavior.
---

# Parent

Parent [[TAS-001-distribution]].

# Result

Codex paths use `.agents/skills`; Claude paths remain `.claude/skills`. The installer emits quoted TOON-style fields on stdout, structured errors, and a fast version path.
