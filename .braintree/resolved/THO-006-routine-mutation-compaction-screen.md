---
context_rev: 2
updated: 2026-09-11T02:46:00Z
summary: Rejected routine-mutation invariant compaction; repaired the zero-live recorder gate without creating benchmark evidence.
---

# Context

Area [[IDX-001-execution-graph]].

# Result

The `routine-mutation-status-v1` fixture exactly checks one active-to-resolved
node move, semantic revision 3→4, fresh UTC timestamp, removed `next`,
preserved Area/dependency pin, no unrelated file changes, graph validity, and
an exact answer artifact. The fixture previously initialized the task at
revision 1 while requiring revision 4, and the runner overwrote its pre-run
session list with fixture content before session lookup. The fake-CLI test now
executes the full mutation/answer/completed-turn/final-telemetry lifecycle and
proves the post-run filesystem gate occurs before cleanup and recording.

The baseline and compact-rule candidate each emitted final cumulative telemetry
but lacked an accepted answer artifact/filesystem gate; they are diagnostics,
not evidence. The repaired gate does not make them eligible, and the wording
must not receive another pair unless existing evidence proves both original
answers correct and the candidate materially better.
