---
context_rev: 1
status: proposed
priority: P3
updated: 2026-09-15T15:07:20Z
summary: Cheapen subprocess-bound default-gate tests to in-process calls.
next: Convert test_packet.py and test_manifest.py reads to in-process main.main with pinned environment.
---

Parent [[tas-69wgeb626grkec6cav2j0bkaeh-audit-and-trim-the-default-test-gate-keep-only]].

# Context

Subprocess-bound default-gate tests:

- Convert packet, manifest, identity, migration, and usage-error tests to
  in-process main.main or cli.main under a pinned environment.
- Keep one python -m tangle entry-point spawn per file.

# Outcome

Those tests exercise the in-process entry point under a pinned environment
rather than paying a subprocess spawn for each assertion.

# Done when

- The named tests run in-process with pinned env.
- One subprocess entry per file remains.
- make test is green.
