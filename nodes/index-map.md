---
updated: 2026-09-12T14:53:52Z
summary: Route agents from the durable execution-graph root hub to authoritative queries.
---

# Root hubs

- Indexes [[IDX-001-execution-graph]]: durable entry for execution-graph work.

# Queries

- Frontier: `braintree frontier`
- Known item: `find nodes -type f -name 'TAS-007-*'`
- Unfinished: `find nodes -type f -name 'TAS-*.md' | rg '/(active|proposed|blocked)/'`
- Blocked: `find nodes -type f -path '*/blocked/TAS-*.md'`
- Highest actionable priority: `find nodes -type f -path '*/active/TAS-*.md' -exec rg -l '^priority: P0$' {} +`
- Changed definition: `braintree impact ID`
- Exceptional lifecycle: `rg -l '^disposition:' nodes`
- Recent: `rg -H '^updated:' nodes | awk -F ': ' '{print $2 " " $1}' | sort -r | head -5`
- Primary routes: `rg -n '^(Parent|Area) \[\[' nodes`

Node files and status directories are authoritative. This file contains intent and recipes, not copied node state.
