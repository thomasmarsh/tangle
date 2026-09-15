---
context_rev: 1
priority: P2
status: proposed
updated: 2026-09-15T14:36:52Z
summary: Add short-prefix and mnemonic node-id resolution to id-accepting commands.
next: Design unambiguous short-prefix resolution for tangle node and other ID-accepting operands, erroring with the matching candidates on ambiguity.
---

Parent [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]].

# Context

`tangle node --help` accepts only a "bare ID or full node name"; new writes generate 26-character lowercase Crockford ids with no shorter human-typable handle. NOTES.md independently flags this as a regression from the earlier `TAS-123`-style legacy names: durable identity is convenient for machines and inconvenient for a human to type or dictate.

# Outcome

An id-accepting command resolves an unambiguous short prefix or an explicit mnemonic alias to its canonical id before use, and reports an ambiguous prefix as a structured list of matching candidates rather than picking one.

# Done when

- A short prefix of a canonical id that matches exactly one node resolves to it in `tangle node` (and other id-accepting commands sharing the same resolver).
- An ambiguous prefix returns every matching candidate's id and summary and exits non-zero rather than guessing.
- A resolved short handle is never written into a canonical file as a durable reference; only the full id is persisted, per the existing rule that a temporary result number must never become a durable reference.
- Tests cover an unambiguous prefix, an ambiguous prefix, a prefix matching zero nodes, and a legacy uppercase id passed unchanged.
- `tangle check` and `make test` pass.
