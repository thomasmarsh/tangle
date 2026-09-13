---
context_rev: 1
priority: P1
updated: 2026-09-11T13:15:00Z
summary: Document and distribute specialized hybrid-store commands without changing Markdown authority.
---

# Context

Parent [[TAS-030-hybrid-markdown-sqlite-migration]].

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

Agents can claim, allocate, reindex, query, and recover through documented commands while Markdown editing and Obsidian viewing stay intact.

# Done when

SKILL.md, README, benchmark guidance, and Codex/Claude installation paths accurately define authority, local-host limits, recovery, and deferred status migration.

# Result

The skill exposes `bt` commands rather than SQLite access, documents the Markdown/sidecar authority split, WAL and PostgreSQL boundary, recovery, and deferred status migration. Codex and Claude installers distribute executable `graph-check.rb`, `bt`, and `bt-index.rb`; installation tests verify their contents and modes.
