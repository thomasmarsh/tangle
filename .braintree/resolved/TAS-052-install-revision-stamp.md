---
context_rev: 2
priority: P2
updated: 2026-09-12T13:32:09Z
summary: Installs record the Braintree version and source revision and report them through the documented `--version` read path.
---

# Context

Parent [[TAS-051-installed-revision-awareness]].

Depends on [[DEC-003-semantic-versioning]] at context_rev 1.

# Outcome

A fresh install copies a machine-readable record of the Braintree release
version and source revision into the installed skill, and the installed
commands report it without network access or the original checkout.

# Done when

- `scripts/install.sh` writes the record on a real install, leaves it untouched
  on a no-op reinstall, and the record changes when the installed revision
  changes.
- The record holds the semantic version declared in `pyproject.toml` and the
  source revision available at install time, and states explicitly when no
  revision can be determined.
- The installed `bt` (and `graph-check`) report the recorded version and
  revision through a documented, stable read path that a consuming project can
  run.
- The semantic version remains declared once and is not hand-edited into a
  second artifact; the record is generated data.
- `tests/install.sh` and the Python suite assert the record exists, matches the
  declared version, and survives a no-op reinstall unchanged.

# Result

The installer now writes a generated `installed-revision` record beside the
installed package: the semantic version from `pyproject.toml` stamped with the
source revision as `<version>+g<short-sha>`, or `<version>+unknown` when the
source revision cannot be determined. Re-running an unchanged install reports
`no-op` and leaves the record and its file mtime untouched; a changed revision
is restamped and reported as `installed`.

Both console scripts read that record through `--version`: the installed `bt`
and `graph-check` print the recorded revision, while a checkout with no record
prints the declared version. `bt --version` is therefore the documented read
path for a `braintree_revision:` value, and the record matches the `FBK`
revision convention `graph-check` enforces. The semantic version is still
declared once in `pyproject.toml`; the record only stamps it as generated data.

Evidence:

- `scripts/install.sh` writes `src/braintree/installed-revision` from the
  declared version and `git rev-parse --short=7 HEAD`, or `+unknown` without git.
- `braintree.revision` resolves the record; `bt` and `graph-check` report it.
- `tests/install.sh` asserts a fresh install records the stamp, a no-op
  reinstall leaves it and its mtime untouched, and a changed revision restamps.
- `tests/test_revision.py` covers the read path and the unknown fallback, and
  `tests/test_skill.py` locks the `SKILL.md` contract; `make test` passes.
