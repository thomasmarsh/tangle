---
context_rev: 1
priority: P2
updated: 2026-09-12T16:40:00Z
summary: Give a gated dependency on an unresolved predecessor a sanctioned representation and a diagnostic that names it.
next: Decide the sanctioned gated-dependency form and improve the diagnostic.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N8: a node that knows it depends on a predecessor which is not yet resolved has
no sanctioned way to record that. An unpinned context edge fails as a missing
pin and a pinned edge fails because the target is not resolved, and neither
diagnostic names the sanctioned form. The contract says to confirm a pinned
dependency is resolved before executing, but not how to gate on one before that
point.

# Outcome

A worker can record a known dependency on an unresolved predecessor without
failing the checker, or is told the one sanctioned alternative in the failure.

# Done when

- `SKILL.md` states how to record a dependency on a predecessor that is not yet resolved, or the checker accepts a bounded not-yet-resolved form.
- The unresolved-target and missing-pin diagnostics name that sanctioned form.
- Regression tests cover the chosen behavior and `make test` passes.
