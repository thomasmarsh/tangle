---
context_rev: 1
priority: P2
updated: 2026-09-12T12:40:14Z
summary: graph-check names trailing text after a dependency link, and SKILL.md states that a context pin must end its line.
next: Add a fixture whose pin has trailing prose and assert that the diagnostic names that text.
---

# Context

Parent [[TAS-044-usage-feedback-hardening]].

Feedback finding F4 (low): `_CONTEXT_PIN` uses `fullmatch` on the text after a
`Depends on [[]]` line, so trailing prose invalidates an otherwise correct pin.
The error says only "invalid or missing context_rev pin".

# Outcome

A pin that is not the last text on its line produces a diagnostic that names the
trailing text, and `SKILL.md` states the line-termination rule where it
introduces the pin syntax.

# Done when

- The checker diagnostic distinguishes a missing pin from a pin followed by
  trailing text and shows the offending suffix.
- `SKILL.md` documents that the pin must terminate the line.
- A fixture test covers the trailing-text case, and `make test` passes.
