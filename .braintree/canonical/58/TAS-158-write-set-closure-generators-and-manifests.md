---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Name workspace manifests, lockfiles, and generated artifacts in the compile-and-golden write-set closure.
---

# Context

Parent [[TAS-153-usage-feedback-hardening-round-eight]].

Hekate `FBK-026` finding 3 at `0.6.0+g3bacaf5`: adding a `glam` dependency to
`apps/hekate-cli` required editing the workspace `Cargo.lock` at the repository
root, outside the declared `apps/hekate-cli/**` write set, so the worker had to
exceed its set or stop. Hekate `FBK-029` finding 1 at the same revision: a leaf
write set omitted the generated `schemas/scenario-source.schema.json` that the
approved source-shape change necessarily regenerates. `references/coordination.md`
states the closure as "every golden and baseline the change can invalidate
(`tests/golden/**`, `baselines/**`)" and names neither manifests, lockfiles, nor
generated artifacts.

# Outcome

The coordination reference's compile-and-golden closure names the workspace
manifest and lockfile when the approved change needs a dependency, and generated
artifacts (JSON schemas, snapshots, pinned-hash fixtures) when a source shape
changes, so a worker never leaves its write set or stops for a necessary closure
file.

# Done when

- The closure enumeration in `references/coordination.md` names workspace
  manifests and lockfiles and generated artifacts.
- A contract test pins the enumeration.
- `make test` passes.

# Result

`references/coordination.md` names the generators and manifests in the
compile-and-golden closure: membership now covers, beyond exhaustive matches
and struct literals on the changed types and `tests/golden/**`/`baselines/**`,
"the workspace manifest and lockfile when the approved change needs a
dependency" and "the generated artifacts a source shape change invalidates
(JSON schemas, snapshots, pinned-hash fixtures)". It states why: a necessary
dependency or regenerated artifact is in the set even though the change edits
no source file in it, so a worker never leaves its set or stops for a closure
file. This closes Hekate `FBK-026` finding 3 (the workspace root `Cargo.lock`
outside `apps/hekate-cli/**`) and Hekate `FBK-029` finding 1 (the regenerated
`schemas/scenario-source.schema.json`).

`tests/test_skill.py` pins the enumeration: `_WRITE_SET_CLOSURE_RULE` now
carries the manifest/lockfile and generated-artifact clauses, and
`test_write_set_is_the_change_closure` asserts them against the reference. The
new `test_write_set_closure_guard_rejects_the_pre_change_enumeration` is the
falsification probe: it feeds the pre-change paragraph through the same
`_assert_contains` guard and requires `AssertionError`, so the test fails when
the guard stops detecting the new clauses rather than passing vacuously.
Running the widened rule against the pre-change `HEAD:references/coordination.md`
leaves exactly those two clauses missing:

```sh
uv run python -c '...'  # widened rule vs. git show HEAD:references/coordination.md
# missing against HEAD: ['the workspace manifest and lockfile when the approved
# change needs a dependency', 'the generated artifacts a source shape change
# invalidates (JSON schemas, snapshots, pinned-hash fixtures)']
```

`braintree check` passes (196 nodes) and `make test` passes. No `context_rev`
bump: no node pins this node, and the added guidance changes no existing
consumer assumption. The parent [[TAS-153-usage-feedback-hardening-round-eight]]
named this node in its write set, so its `next` advanced to
[[TAS-159-timed-out-worker-recovery]] in this change.
