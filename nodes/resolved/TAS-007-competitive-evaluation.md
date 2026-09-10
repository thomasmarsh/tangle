---
rev: 3
priority: P0
updated: 2026-09-10T11:30:00Z
summary: Finalized V3 with a colocated routing index and authoritative status directories.
---

# Context

Preserve existing repository work. Keep generated fixtures outside the repository. The tested V3 layout uses authoritative status directories, a routing-only index, compact executable headers, and local dependency revision pins.

# Result

Independent evaluators completed all four baselines and three alternative rounds at small, 1,000-node, and 10,000-node scales. The final V3 contract colocates its routing-only index at `nodes/index-map.md`, removes the global write hotspot, reduces the 10,000-node corpus, and makes pinned dependency staleness decidable in two operations. BENCHMARK.md records the normalized evidence and tradeoffs.
