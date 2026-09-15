---
context_rev: 1
priority: P2
status: proposed
updated: 2026-09-15T14:36:52Z
summary: Add an installation diagnostic surface and diagnose the reported duplicate pi install.
next: Implement a diagnostic command reporting every discovered skill/program copy per agent and scope, then run it to diagnose the duplicate pi report.
---

Parent [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]].

# Context

ASTRA.md: "The reported duplicate pi skill deserves a targeted diagnosis. I did not inspect the user's installed skill directories, so the cause is unconfirmed." No `tangle` command currently reports which copies of the skill/program an agent will discover across home and project scopes; `tangle location` reports only this project's own state path.

# Outcome

A diagnostic surface lists every discovered skill and program copy per agent and scope with its version, so a duplicate-discovery report is confirmable from the tool instead of manual directory inspection, and the specific reported pi duplication is diagnosed and, if real, given an explicit repair path.

# Done when

- A command enumerates installed skill/program copies across home and project scopes for each supported agent (codex, claude, pi) with path and version.
- Running it against the environment that reported duplicate pi discovery either reproduces and explains the duplication or establishes it does not reproduce here, with evidence recorded in the result.
- A confirmed duplication path has an explicit repair instruction (which copy to remove, or how installation should have deduplicated).
- Tests cover a single clean install, a genuine duplicate across scopes, and a missing installation.
- `tangle check` and `make test` pass.
