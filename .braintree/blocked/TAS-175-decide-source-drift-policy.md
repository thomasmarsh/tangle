---
context_rev: 1
updated: 2026-09-14T02:16:27Z
summary: Decide the source-drift and authority-conflict policy for living plans.
next: Answer how reviewed source changes should be detected and reconciled.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-171-pilot-incremental-plan-intake]].

Drift support is conditional on a living source or incomplete migration. A frozen historical plan may need identity evidence but no ongoing watcher.

# Outcome

A settled policy defines which source changes matter, when reconciliation runs, and how conflicts with admitted graph authority are surfaced.

# Done when

- The policy distinguishes source-only narrative changes, changes to not-yet-admitted work, changes contradicting an admitted fact, edits to graph-owned checklist status, and formatting-only changes.
- It defines source identity and comparison granularity using Git revisions, whole-file hashes, section hashes, or a justified alternative.
- It specifies manual, on-read, check-time, or explicit-command reconciliation cadence.
- Authority violations remain visible conflicts and are never silently synchronized.
- It defines behavior for moved or renamed files and headings, deleted sections, rebases, uncommitted edits, and unavailable source repositories.
- If automated drift support is not justified, [[TAS-176-build-source-drift-reconciliation]] is explicitly disposed.

# Blocked

Blocked by: project-owner choices about source lifetime and acceptable reconciliation behavior.

Questions for the project owner:

1. Which coexistence modes need drift detection rather than a one-time source stamp?
2. Should reconciliation run explicitly, during ordinary reads, or as a non-failing advisory in check or status output?
3. Must sources be Git-tracked, or should uncommitted and external documents be supported?
4. Should identity be file-level or section-level, given that headings and prose may be rewritten?
5. When source text contradicts graph-owned execution state, should the tool warn only, block execution, or require an explicit disposition?
6. How should formatting-only and section-move changes be distinguished from semantic drift?
7. What ongoing maintenance cost is acceptable for a permanent hybrid project?

Unblocks when: the owner answers these lifecycle and enforcement questions after pilot drift evidence is available.
