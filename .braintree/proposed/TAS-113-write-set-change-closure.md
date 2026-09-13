---
context_rev: 1
priority: P2
updated: 2026-09-13T02:14:00Z
summary: Define an exclusive write set as the compile-and-golden closure of its change, not a crate directory, and say what a worker does when the closure exceeds the assigned set.
next: Add the change-closure write-set rule to the coordination reference and pin it.
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
