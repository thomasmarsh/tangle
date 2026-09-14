---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Every project using Braintree can name its installed version and revision offline, and migration is a settled deliberate decision.
---

# Context

Area [[IDX-001-execution-graph]].

Depends on [[DEC-003-semantic-versioning]] at context_rev 1.

# Outcome

An installation of Braintree records the released version and the source
revision it was copied from, exposes that record to the consuming project
through a documented read path, and leaves any migration of installs or vaults
as an explicit, unevaluated future decision.

# Done when

- A consuming project can read the Braintree version and source revision its
  installed skill came from without network access or the source repository.
- The recorded revision is generated install data, not a second hand-maintained
  source of the semantic version, per [[DEC-003-semantic-versioning]].
- No migration code, compatibility shim, or data rewrite ships as part of this
  work.
- [[TAS-053-version-migration-evaluation]] records the trigger conditions under
  which a migration would be considered.
- Tests cover a fresh install, a no-op reinstall, and an upgrade where the
  recorded revision changes.
- Every child is resolved or disposed with rationale.

# Result

Installs record `<version>+g<short-sha>` and report it through `bt --version`
and `graph-check --version`, so a consuming project can name its installed
version and revision offline ([[TAS-052-install-revision-stamp]]).
[[TAS-053-version-migration-evaluation]] settled the migration policy in
[[DEC-005-reinstall-not-migration]]: benign version gaps are reconciled by
reinstalling, the sidecar is rebuilt rather than migrated, and only an
incompatible change to the installed skill/CLI contract or the vault Markdown
format would force a vault migration. The revision is generated install data,
and no migration code or compatibility shim shipped. `tests/install.sh`,
`tests/test_revision.py`, and `tests/test_scaffold.py` cover a fresh install, a
no-op reinstall, and a changed revision; `make test` passes.
