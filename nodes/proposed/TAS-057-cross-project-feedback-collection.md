---
context_rev: 1
priority: P1
updated: 2026-09-12T13:14:11Z
summary: A maintainer scans external vaults' nodes/ and gets Braintree feedback as a compact result ready for triage into this graph.
next: Define the scan command and triage output over the settled feedback contract.
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
