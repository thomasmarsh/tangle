---
status: resolved
context_rev: 2
priority: P3
updated: 2026-09-14T23:40:13Z
summary: Version gaps are reconciled by reinstalling; migration is warranted only by an incompatible change to the installed skill/CLI or vault Markdown contract.
---

# Context

Parent [[TAS-051-installed-revision-awareness]].

Depends on [[DEF-001-distribution-contract]] at context_rev 1.
Depends on [[DEC-003-semantic-versioning]] at context_rev 1.

# Outcome

A settled decision records whether installed Tangle revisions need
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

# Result

Settled in [[DEC-005-reinstall-not-migration]]. A version gap is benign unless
it changes one of the two versioned contract surfaces — the installed skill and
CLI contract, or the vault Markdown format — incompatibly. Benign gaps are
reconciled by reinstalling; the sidecar is rebuilt, never migrated. The public
`<version>` is the offline compatibility signal and `+g<short-sha>` is
provenance only. The "a behavior change bumps the version" rule stays a
convention backed by the single-source version test, the `tests/test_skill.py`
contract locks, and conventional commits; a diff-based gate is rejected, and a
MAJOR break must name its migration path in its own `DEC`. No migration code or
data rewrite was added.
