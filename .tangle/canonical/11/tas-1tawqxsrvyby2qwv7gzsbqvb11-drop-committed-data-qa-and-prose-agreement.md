---
context_rev: 1
status: proposed
priority: P3
updated: 2026-09-15T15:07:20Z
summary: Drop committed-data QA and prose-agreement tests from memory corpus modules.
next: Remove the subsumed per-family structure tests and record the surviving whole-corpus verifier.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

The memory corpus modules carry committed-data QA and prose-agreement tests:

- Per-family generic structure tests are subsumed by the test_memory_corpus.py
  whole-corpus verify.
- Prose-agreement tests across the memory modules assert documentation, not
  behavior.
- Keep unique per-family invariants and the corpus validator contract tests.

# Outcome

The memory corpus modules test only unique per-family invariants; shared
structure and prose agreement are owned once by test_memory_corpus.py.

# Done when

- Subsumed tests are removed.
- Unique invariants and test_memory_corpus.py remain.
- make test is green.
