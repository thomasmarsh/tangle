---
context_rev: 1
priority: P2
updated: 2026-09-12T16:40:00Z
summary: Stop the checker from parsing wikilink-shaped tokens inside inline code spans and fenced code blocks as real links.
next: Mask code spans and fences before the link scan.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N4: the checker scans raw node text, so a node that quotes the skill's own
grammar in code font or a fenced block produces a spurious `broken link`
finding. This is a recurrence of the round-two source `Tangle THO-008 F2`; the
current workaround is to never reproduce a link-shaped token in any node text.

# Outcome

Quoting a wikilink-shaped token in code is not a graph error, while real
wikilinks remain validated.

# Done when

- Inline code spans and fenced code blocks are excluded from link scanning.
- A quoted token in code produces no `node-broken-link` finding, and a real wikilink beside it still validates.
- Regression tests cover inline and fenced forms and `make test` passes.
