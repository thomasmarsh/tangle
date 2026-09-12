---
context_rev: 2
priority: P3
updated: 2026-09-12T13:43:19Z
summary: Decide when a Braintree version gap justifies migration, naming the compatibility surfaces and the version-versus-revision division of labor.
next: Name the versioned contract surfaces, then classify benign versus behavior-changing gaps.
---

# Context

Parent [[TAS-051-installed-revision-awareness]].

Depends on [[DEF-001-distribution-contract]] at context_rev 1.
Depends on [[DEC-003-semantic-versioning]] at context_rev 1.

# Outcome

A settled decision records whether installed Braintree revisions need
migration, names the change kinds that would force one, and describes the
authority, recovery, and validation a future migration would need. It also
names the contracts the semantic version is a compatibility promise about: the
installed skill and CLI contract, and the vault Markdown format. It fixes the
division of labor between the public `<version>` (compatibility) and the
`+g<short-sha>` build metadata (provenance). No migration ships.

# Done when

- The evaluation separates benign revision gaps from gaps that change
  vault-observable or sidecar-observable behavior.
- It names the versioned contract surfaces explicitly and says which field a
  consumer compares for an offline compatibility decision.
- It states whether the semantic version can carry that promise as enforced
  today, or whether the "behavior change bumps the version" rule in
  [[DEC-003-semantic-versioning]] needs enforcement to make a gap meaningful.
- It names concrete trigger conditions that would justify a migration and the
  minimum evidence required to act on them.
- It records the settled choice as a `DEC` node rather than leaving the question
  open.
- No migration code, data rewrite, or compatibility shim is added.
