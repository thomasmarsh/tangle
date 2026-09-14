---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: Delivered an optional stateless graph integrity check with fixture coverage and installed distribution.
---

# Context

Parent [[TAS-008-fit-for-purpose-hardening]].

# Finding

Manual discipline is unlikely to preserve all graph invariants over thousands of nodes and years of edits. Repository tests validate part of the current graph, but installed projects receive the skill contract rather than a reusable graph checker.

# Intended change

Provide one optional, read-only, zero-state validation command suitable for local grooming and CI. Check duplicate identities, broken links, required frontmatter, status and `next` consistency, unpinned context edges, revision mismatches, orphan unfinished nodes, and parent cycles. Keep normal reads and mutations independent of the checker, database, cache, or daemon.

# Result

Added `scripts/graph-check.rb`, a standard-library Ruby checker that reads a selected nodes directory without writing state. It is installed for Codex and Claude Code projects, documented for local grooming and CI, and tested against valid plus deliberately invalid fixture graphs. It validates canonical reciprocal edges and direct-child frontiers in addition to the stated integrity rules.
