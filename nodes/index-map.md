---
updated: 2026-09-10T11:30:00Z
summary: Route agents from the colocated graph entry point to authoritative queries.
---

# Queries

- Known item: `find nodes -type f -name 'TAS-007-*'`
- Unfinished: `find nodes -type f -name 'TAS-*.md' | rg '/(active|proposed|blocked)/'`
- Blocked: `find nodes -type f -path '*/blocked/TAS-*.md'`
- Highest actionable priority: `find nodes -type f -path '*/active/TAS-*.md' -exec rg -l '^priority: P0$' {} +`
- Changed definition: `rg -n -F 'Depends on [[DEF-ID]] at rev ' nodes`
- Exceptional lifecycle: `rg -l '^disposition:' nodes`
- Recent: `rg -H '^updated:' nodes | awk -F ': ' '{print $2 " " $1}' | sort -r | head -5`

Node files and status directories are authoritative. This file contains intent and recipes, not copied node state.
