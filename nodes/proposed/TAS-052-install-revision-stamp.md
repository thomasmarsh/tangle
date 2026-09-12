---
context_rev: 1
priority: P2
updated: 2026-09-12T13:14:11Z
summary: Install records the Braintree version and source revision and exposes them through a documented read path.
next: Define the revision record format and write it from scripts/install.sh.
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
