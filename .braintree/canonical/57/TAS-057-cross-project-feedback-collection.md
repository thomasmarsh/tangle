---
status: resolved
context_rev: 1
priority: P1
updated: 2026-09-14T23:40:13Z
summary: A maintainer scans external vaults' nodes/ and gets Braintree feedback as a compact result ready for triage into this graph.
---

# Context

Parent [[TAS-054-feedback-mechanism]].

Depends on [[TAS-055-feedback-node-contract]] at context_rev 1.

# Outcome

A maintainer points the tooling at one or more external vaults and receives the
Braintree feedback they contain as a compact, bounded list that can be triaged
into admitted work in this graph.

# Done when

- A documented command or recipe scans the `nodes/` of one or more external
  vaults and returns only feedback under the convention, without reading every
  node body by hand and without writing to the scanned vault.
- The result is compact TOON with the fields needed to triage, such as feedback
  id, status, Braintree revision, and summary, and it states zero results
  explicitly.
- The scan works on a read-only checkout and needs no sidecar or network.
- `SKILL.md` documents the triage step that maps accepted feedback to admitted
  nodes here and disposes the rest.
- A test runs the scan against a fixture vault and asserts both a populated
  result and an explicit zero result.

# Result

The read-only `feedback-scan` command scans one or more vault roots (or their
`nodes/` directories), reads only `FBK-*.md` filenames and frontmatter, and
prints compact TOON rows of `vault,id,status,revision,summary`. It prints
`feedback: 0 nodes` for an explicit zero, accepts an optional `--limit` bound,
and never opens the sidecar, touches the network, or writes to a scanned vault.
`SKILL.md` documents the scan and the triage step that admits feedback likely to
change a future decision or action, cites the feedback id and revision, and
otherwise disposes the result explicitly.

Evidence:

- `src/braintree/feedback_scan.py` is a stdlib-only collector over `toon.py`,
  with `scripts/feedback-scan` and the `feedback-scan` console script in
  `pyproject.toml`.
- `tests/test_feedback_scan.py` seeds a fixture vault and asserts the populated
  result, the explicit zero result, multi-vault collection, the `--limit`
  bound, a nodes-directory argument, usage errors, and that the vault is
  unchanged after a scan.
- `tests/test_skill.py` pins the `feedback-scan` and triage contract strings;
  `tests/install.sh` runs the installed console script.
- `make test` passes.
