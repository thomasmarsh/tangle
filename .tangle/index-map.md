---
updated: 2026-09-14T23:48:31Z
summary: Route agents from the durable execution-graph root hub to authoritative queries.
---

# Root hubs

- Indexes [[IDX-001-execution-graph]]: durable entry for execution-graph work.

# Queries

- Frontier: `tangle frontier`
- Known item: `find .tangle -type f -name 'TAS-007-*'`
- Unfinished: `rg -l '^status: (proposed|active|blocked)$' .tangle`
- Blocked: `rg -l '^status: blocked$' .tangle`
- Highest actionable priority: `rg -l '^priority: P0$' .tangle | xargs rg -l '^status: active$'`
- Changed definition: `tangle impact ID`
- Exceptional lifecycle: `rg -l '^disposition:' .tangle`
- Recent: `rg -H '^updated:' .tangle | awk -F ': ' '{print $2 " " $1}' | sort -r | head -5`
- Primary routes: `rg -n '^(Parent|Area) \[\[' .tangle`

Node files are authoritative; the status field is authoritative for a stationary node and the status directory is legacy. This file contains intent and recipes, not copied node state.
