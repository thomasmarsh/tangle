---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: DEC nodes retain settled choices, rationale, and consequences as current knowledge.
---

# Context

Parent [[TAS-013-decision-memory]].

# Decision

Use `DEC` filenames for durable settled choices that need to remain understandable after the decision work ends.

# Rationale

Tasks and definitions can contain decisions incidentally, but neither consistently preserves why a cross-cutting choice was made or what it changes.

# Consequences

Record only the choice, its material rationale, and its operational consequences. Resolve the node when that choice is formed; it remains current unless `disposition: deprecated` or `disposition: superseded` is added.
