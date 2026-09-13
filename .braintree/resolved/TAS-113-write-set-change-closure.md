---
context_rev: 1
priority: P2
updated: 2026-09-13T02:20:06Z
summary: Define an exclusive write set as the compile-and-golden closure of its change, not a crate directory, and say what a worker does when the closure exceeds the assigned set.
---

# Context

Parent [[TAS-111-usage-feedback-hardening-round-six]].

Tangle `FBK-008` at `0.5.0+gf9b330c` and its additional evidence Tangle
`FBK-009` at `0.5.0+g974b178`, verified in
[[THO-017-round-six-usage-feedback-analysis]]. A deliberate record change
forced edits outside the handed-off crate-local set: the record shape is
re-declared in `apps/tangle-cli` with an exhaustive `EventRecord` match, and
the invalidated goldens and `baselines/` live outside every crate directory;
the presentation golden is a whole-frame `Debug` dump, a closure member of any
public-field change. `references/coordination.md` grants authoring "inside its
declared write set" and escalation for "a change that alters a landed seam
another node owns", but states no rule for a closure that exceeds the assigned
set; a worker had to widen the set itself. `FBK-009` is merged here because it
is the same outcome and needs no separate acceptance.

# Outcome

A slice write set is the compile-and-golden closure of its approved change, not
a crate directory: the handoff names, or the worker derives and records, every
file the change must touch — exhaustive matches and struct literals on the
changed types, plus every golden and baseline the change can invalidate — and a
worker that finds an in-scope closure member reports the addition instead of
guessing or stalling, while a member in another node or a shared hub is still
escalated.

# Done when

- `references/coordination.md` states that the assigned write set is the compile-and-golden closure of the change, naming what membership covers (exhaustive matches and struct literals on changed types, and every golden and baseline the change can invalidate).
- `references/coordination.md` states what a worker does when the closure exceeds the assigned set: report and include the additional in-scope paths, versus stop and escalate for a path owned by another node or a shared hub.
- A contract test in `tests/test_skill.py` pins the stated rule.
- `make test` passes.

# Result

`references/coordination.md` defines the assigned write set as the compile-and-golden closure of the approved change, and `tests/test_skill.py` pins the rule.

- Under `## Parallel worktree contract`, beside the slice-authoring bullet, the reference now states: "The assigned write set is the compile-and-golden closure of the approved change, not a crate directory: membership covers every file the change must touch, including exhaustive matches and struct literals on the changed types, plus every golden and baseline the change can invalidate (`tests/golden/**`, `baselines/**`). When the closure exceeds the assigned set, the worker includes and reports the additional in-scope paths; it stops and escalates for a path owned by another node or a shared hub."
- `tests/test_skill.py` adds the `_WRITE_SET_CLOSURE_RULE` constant and `test_write_set_is_the_change_closure`, which reads `references/coordination.md` through the existing `_reference` helper in the neighbours' literal-substring style. Removing the rule text fails the test (`1 failed`); restoring it passes.
- `FBK-007`'s secondary note, an integration test needing a genuinely public crate surface, is a closure member of this rule and needs no further node.

Evidence: `make test` ran 365 passed, 3 skipped, 79 deselected in 41.04s; `uv run pytest tests/test_skill.py -q` passed 57; the deliberate-removal probe failed as intended; `braintree check` passed.
