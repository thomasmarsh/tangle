---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Require a node or increment brief to name the existing test suites that enumerate a directory the artifact enters.
---

# Context

Parent [[TAS-153-usage-feedback-hardening-round-eight]].

Hekate `FBK-028` finding 1 at `0.6.0+g3bacaf5`: adding the first version-2
scenario under `scenarios/` broke
`apps/hekate-cli/tests/migration_regression.rs`, whose gate required every
checked-in `*.json5` under that directory to be a version-1 source that migrates
and reproduces the original reader's body. Neither `SKILL.md` nor the task brief
named any test gate that enumerates the directory a new artifact lands in, so the
collision was avoidable only by knowing the gate existed before choosing the
artifact path. No match for `enumerat|gates my artifact|test suite` in
`SKILL.md` or `references/`.

# Outcome

The authoring or coordination reference requires a node or increment brief to
carry a "gates my artifact enters" line naming the existing test suites that
enumerate a directory a new artifact path enters.

# Done when

- The rule is in `references/coordination.md` or `references/authoring.md` and
  pinned by a contract test.
- The rule names the directory-enumerating gate as the thing a brief must
  surface before the artifact path is chosen.
- `make test` passes.

# Result

`references/authoring.md` carries the rule in "Decomposition and roll-up", after
the child-brief sentence: an increment brief — a node's body or a worker handoff
— that places a new artifact in an existing directory carries a "gates my
artifact enters" line naming the test suites that enumerate that directory,
before the artifact path is chosen. It states why: a gate that walks a directory
and asserts a property of every file in it can reject a correctly authored new
file, so the enumerating suite is a path constraint the brief surfaces rather
than a verification surprise. The Hekate collision is exactly this shape: a
version-2 scenario added under `scenarios/` was rejected by
`apps/hekate-cli/tests/migration_regression.rs`, which enumerates the directory.

`tests/test_skill.py` pins the rule as `_ENTERED_GATE_BRIEF_RULE` with
`test_brief_names_the_gates_an_entered_directory_enumerates`, asserting the
brief form, the "gates my artifact enters" line, the path-choice ordering, and
the directory-walking gate. The guard rejects the pre-change reference: all four
substrings are absent from `HEAD:references/authoring.md`, so the test fails when
the rule is removed rather than passing vacuously. No separate falsification
fixture is required, because this is a reference contract string and not a
source-text negative assertion.

`braintree check` passes and `make test` passes. No `context_rev` bump: the rule
is new guidance for future briefs, no existing node pins this node, and no
consumer assumption changes.
