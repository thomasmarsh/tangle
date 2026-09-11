---
context_rev: 1
priority: P1
updated: 2026-09-10T21:11:54Z
summary: Made empty-vault bootstrap deterministic and graph-checker valid.
---

# Context

Area [[IDX-001-execution-graph]].

# Outcome

Align the empty-vault bootstrap procedure with the root-hub reachability contract.

# Result

Bootstrap instructions now create an indexed resolved/current `IDX` root hub
before the first actionable node and give that node its primary route. The
graph-checker tests exercise this minimal bootstrap vault. Corrected the
storage-comparison description to say it evaluates four representations.
