---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: graph-check names trailing text after a context pin and SKILL.md states that a pin must end its line.
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

# Result

The checker now accepts only a pin that terminates the line and, when a valid
pin is followed by prose, reports
`context_rev pin for the target has trailing text: <suffix>`. `SKILL.md` states
that the pin must terminate its line.

Evidence:

- `test_context_pin_with_trailing_text_names_it` asserts the diagnostic names
  `and more context.`, while `test_missing_context_rev_pin` still reports the
  missing-pin case.
- `SKILL.md` dependency-revision section states the line-termination rule.
- `make test` passes.
