---
context_rev: 1
priority: P1
updated: 2026-09-11T11:29:10Z
summary: Define the coordinator and worker ownership contract for parallel worktrees.
---

# Context

Parent [[TAS-021-parallel-agent-hardening]].

# Outcome

`SKILL.md` states that Focus, active status, and priority are advisory rather than claims; a coordinator assigns each worker a direct node path and exclusive write set; one agent writes a node and its status path at a time; shared parents, `index-map.md`, definitions, and root hubs are coordinator-owned or explicitly serialized; worktree state is a snapshot rather than global truth; and only the coordinator resolves a parent after integrating child evidence.

# Done when

The skill and its contract tests enforce every ownership, snapshot, serialization, and parent-resolution rule without presenting advisory graph state as a lock.

# Result

Added the concise parallel-worktree contract and focused `tests/skill.sh` assertions for advisory state, exclusive ownership, serialization, snapshots, and coordinator-only parent resolution.
