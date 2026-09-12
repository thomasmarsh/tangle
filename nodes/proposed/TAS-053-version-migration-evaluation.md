---
context_rev: 1
priority: P3
updated: 2026-09-12T13:14:11Z
summary: Decide when a Braintree revision gap justifies a migration and what one would require, without implementing one.
next: Record which revision gaps are benign and the evidence that would justify a migration.
---

# Context

Parent [[TAS-051-installed-revision-awareness]].

Depends on [[DEF-001-distribution-contract]] at context_rev 1.

# Outcome

A settled decision records whether installed Braintree revisions need
migration, names the change kinds that would force one, and describes the
authority, recovery, and validation a future migration would need. No migration
ships.

# Done when

- The evaluation separates benign revision gaps from gaps that change
  vault-observable or sidecar-observable behavior.
- It names concrete trigger conditions that would justify a migration and the
  minimum evidence required to act on them.
- It records the settled choice as a `DEC` node rather than leaving the question
  open.
- No migration code, data rewrite, or compatibility shim is added.
