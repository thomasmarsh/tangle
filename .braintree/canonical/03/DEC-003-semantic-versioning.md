---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: The project ships one semantic version declared once in pyproject.toml; every user-visible change bumps it and no artifact freezes or duplicates the number.
---

# Context

Parent [[TAS-001-distribution]].

The port in [[TAS-042-retarget-installers-tests-docs-and-remove-ruby]] instructed preserving `--version 0.3.1` so a mechanical refactor could prove byte-identical behavior. That was a one-time regression guard, not a permanent pin. [[TAS-006-help-contract]] owns the installer help contract.

# Decision

Version the project as one release artifact with a single semantic version, declared once in `pyproject.toml` and never duplicated as a literal elsewhere. The Python package reads it back from installed metadata, and `scripts/install.sh` reads it from `pyproject.toml`. Apply semantic versioning: MAJOR for incompatible contract changes, MINOR for backward-compatible capability, and PATCH for backward-compatible fixes. Never freeze, pin, or treat a version number as an invariant; a change that alters observable behavior bumps the version in the same change.

# Rationale

One project, one version. Separate installer and package numbers let a single distribution report two different releases, which misleads humans and version probes alike. A single declared source removes the duplication that lets them drift, while semantic versioning keeps the number a signal of what changed. Freezing it conflates "behavior is identical" with "behavior must stay identical", turning every legitimate bump into an apparent regression.

# Consequences

The unified version is `0.4.0` after the added pi install target, a backward-compatible capability. Tests derive the expected version from `pyproject.toml` rather than repeating it, so one bump propagates: `tests/install.sh` and `tests/bt-foundation.sh` read the file, and `tests/test_scaffold.py` asserts the declared version matches the installed package metadata. `src/braintree/__init__.py` no longer holds a version literal. The preservation clause in [[TAS-042-retarget-installers-tests-docs-and-remove-ruby]] is historical, describing that single port, and does not constrain later releases. This replaces the earlier per-artifact wording of this decision.
