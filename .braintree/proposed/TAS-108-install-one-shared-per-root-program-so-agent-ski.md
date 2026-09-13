---
context_rev: 1
updated: 2026-09-13T01:31:03Z
summary: Install one shared per-root program so agent skill reinstalls never repoint the command.
next: Specify the shared program location, launcher target, and revision-drift handling, then implement them.
---

Area [[IDX-001-execution-graph]].

# Context

Depends on [[DEC-007-install-one-shared-per-root-program-per-agent-in]] at context_rev 1.

# Outcome

`<root>/.local/bin/braintree` points at one shared per-root program location, and
each agent install copies only its skill prose, so installing or reinstalling an
agent never changes the command target or duplicates the dependency environment.
The optional `--semantic` extra and its zero-config provider default still work.

# Done when

The installer maintains one shared program per root, agent installs copy only
prose and agent metadata, installing one agent leaves the launcher target and the
shared program revision unchanged, `tests/install.sh` covers the no-repoint and
single-program properties, the README describes the layout, and `make test`
passes.
