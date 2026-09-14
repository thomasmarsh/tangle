---
status: resolved
context_rev: 2
updated: 2026-09-14T23:40:13Z
summary: Version gaps are reconciled by reinstalling, not migrating; only an incompatible change to the installed skill/CLI contract or the vault Markdown format would force a deliberate vault migration.
---

# Context

Parent [[TAS-051-installed-revision-awareness]].

Depends on [[DEC-003-semantic-versioning]] at context_rev 1.
Depends on [[DEF-001-distribution-contract]] at context_rev 1.

# Decision

An installed Braintree skill is upgraded by reinstalling it over the previous
copy; the tool never migrates itself or a consuming vault, except for the one
time vault layout rewrite [[DEC-008-vault-lives-under-dot-braintree]] defines
and sanctions. The public semantic
`<version>` is the offline compatibility signal; the `+g<short-sha>` install
record is provenance only and is never ordered or resolved against the remote.
A version gap warrants a migration only when it changes one of the versioned
contract surfaces incompatibly. Every other gap is benign and reconciled by a
plain reinstall.

The versioned contract surfaces are:

- The vault Markdown format: the fixed status-directory names, the node
  filename/type set, the required frontmatter fields and their lifecycle
  meaning, canonical edge direction, dependency-pin syntax, the `index-map.md`
  contract, and the `FBK` node contract.
- The installed skill and CLI contract: the `SKILL.md` instructions and the
  documented inputs, outputs, and exit behavior of `bt`, `graph-check`,
  `feedback-scan`, and `feedback-record`, including the `installed-revision`
  read path.

The sidecar schema is deliberately not a versioned surface: it is derived,
disposable local state, discarded and rebuilt with `bt init` and `bt reindex`,
never migrated.

## Enforcement

As enforced today the semantic version cannot guarantee the promise on its own.
The "a behavior change bumps the version" rule in
[[DEC-003-semantic-versioning]] is a convention, not a mechanical gate: a
single-declared-version test, `tests/test_skill.py`'s locked `SKILL.md`
contract strings, and the conventional-commit types in `AGENTS.md` make a
surface change visible, but nothing fails when a surface changes without a
bump. A diff-based gate is rejected: behavior is not derivable from a file
list, it would misfire on documentation-only edits to the same files, and a
blanket bump defeats it. The gap is made meaningful instead by naming the
surfaces above and requiring every change to one of them to carry its version
bump and a `feat`/`fix` commit in the same change. This rule needs no new
tooling.

# Rationale

Install is a copy, not a dependency, so there is no package manager to run
migrations and no installed consumer to schedule one. The vault is Markdown in
the consumer's own Git repository, where a rewrite is visible and recoverable,
so migration is a deliberate, evidence-backed vault rewrite; the single
sanctioned exception is the layout rewrite above, whose trigger, idempotency,
recovery, and validation [[DEC-008-vault-lives-under-dot-braintree]] defines.
Semantic versioning already separates compatibility
(the version) from provenance (the revision), so a consumer can decide from
`bt --version` alone whether an installed skill can read the vault it holds.
Naming the two surfaces turns "behavior change" from an intuition into a short,
checkable list, which is the minimum enforcement the current copy-install
distribution needs.

# Consequences

Benign gap, no migration. Implementation refactors, performance work, internal
documentation, and any backward-compatible change that leaves both surfaces
readable and writable by the previous installed version. The consumer may
reinstall at leisure; the sidecar may need `bt reindex`, but no vault data is
rewritten.

Behavior-changing gap. A MAJOR change to a named surface. An older installed
skill may misread, reject, or corrupt a vault written by the newer one, or a
consumer's automation may call a changed CLI verb. The action is to reinstall
the newer skill; a vault migration is warranted only when a consumer's files
already hold newer-format data that older tooling must still read.

Migration triggers. One of: (1) a MAJOR change to the vault Markdown format, or
(2) a MAJOR change to the documented CLI contract, or (3) observed `FBK`
friction from a real consumer that traces to a version gap and would be
resolved by migrating rather than reinstalling. Minimum evidence to act: a
minimal reproduction in which the older installed skill mis-reads, rejects, or
corrupts a vault (or a consumer automation fails), the exact version pair, and
a written compatibility note naming the broken surface.

Authority, recovery, and validation if a trigger fires. Markdown stays
authoritative: any migration is a Markdown rewrite in the consumer's Git
repository, recorded as a node there, never a sidecar migration. Recovery is
the consumer's Git history plus the untouched `installed-revision` record; the
migration must be idempotent and must not destroy the pre-migration stamp.
Validation is `braintree check` passing on the migrated vault, `braintree
index` reporting no stale pins, and a rollback path to the prior commit. No
migration code or shim ships before its own `DEC` defines the one-way rewrite,
its trigger, and this recovery and validation plan. [[DEC-008-vault-lives-under-dot-braintree]]
is that `DEC` for the vault layout change.
