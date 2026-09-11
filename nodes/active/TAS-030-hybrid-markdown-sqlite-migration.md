---
context_rev: 1
priority: P0
updated: 2026-09-11T12:40:54Z
summary: Convert this graph project to a Markdown-canonical, SQLite-assisted local execution store.
next: Start [[TAS-031-sidecar-coordination-foundation]].
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[DEC-002-hybrid-markdown-sqlite-authority]] at context_rev 1.

Depends on [[DEF-002-hybrid-store-contract]] at context_rev 1.

# Outcome

This repository exposes a tested specialized command surface for an external local SQLite sidecar while preserving the Obsidian-readable Markdown graph as durable authority.

# Done when

The coordination sidecar, derived index/query path, skill and installation contract, and verification evidence are complete; all created child tasks are resolved or explicitly disposed.
