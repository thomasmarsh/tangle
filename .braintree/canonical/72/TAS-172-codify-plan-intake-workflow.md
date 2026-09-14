---
status: proposed
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Codify the validated plan-intake and hybrid-use workflow.
next: Reconcile pilot evidence into the skill contract, documentation, and tests.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-171-pilot-incremental-plan-intake]].

# Outcome

The Braintree contract teaches the proven coexistence modes, authority boundary, bridge, incremental extraction, reconciliation, migration completion, and rollback behavior without implying automatic document authority.

# Done when

- SKILL.md and the appropriate topical reference state the supported modes and recommended default.
- The contract includes the authority matrix, bridge shape, manual intake procedure, reconciliation triggers, full-migration completion rule, and source-preservation rule.
- Examples distinguish narrative, requirements, decisions, active outcomes, speculation, completed history, stale checklists, and contradictions.
- The contract says headings and chunks are not node boundaries, source retrieval is not admission, and execution state cannot remain editable in both surfaces.
- README contains only the user-facing entry point and routes detailed workflow prose to the owning reference.
- Contract tests pin every invariant whose accidental removal would recreate dual authority or automatic graph extraction.
- Pilot-driven corrections are recorded with evidence rather than silently generalized.
