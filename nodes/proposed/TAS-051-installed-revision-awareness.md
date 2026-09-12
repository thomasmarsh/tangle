---
context_rev: 1
priority: P2
updated: 2026-09-12T13:14:11Z
summary: Every project using Braintree can name the exact installed Braintree revision, and migration stays a deliberate future decision.
next: Start [[TAS-052-install-revision-stamp]].
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
