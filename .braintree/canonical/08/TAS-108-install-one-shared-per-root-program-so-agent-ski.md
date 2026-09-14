---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Install one shared per-root program so agent skill reinstalls never repoint the command.
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

# Result

One shared program per root. `scripts/install.sh`, and `scripts/install-claude.sh`
which delegates to it, now installs the runnable distribution once at
`<root>/.local/share/braintree` and generates `<root>/.local/bin/braintree` to run
that location, never an agent destination. Each agent install copies only the
skill prose it discovers (`SKILL.md`, the `references/` tree, and
`agents/openai.yaml` for Codex) into its own destination. The shared program is
refreshed only when a copied file or its `installed-revision` record differs from
the checkout, which is the revision-drift check; when it matches, an agent
install leaves it untouched. The launcher still requests the optional extra and
defaults `BT_SEMANTIC_PROVIDER` only for `--semantic`, unchanged but now
pointing at the shared program.

`tests/install.sh` proves the layout offline. (a) After installing Codex, then
pi, then Claude Code into one root, the launcher bytes and mtime and the shared
program record bytes and mtime are unchanged, and the launcher still runs
`--project <root>/.local/share/braintree`. (b) Each agent destination holds no
program (`pyproject.toml`, `uv.lock`, and `src` absent) and the root holds
exactly one `installed-revision`. The test also checks the shared program tree,
the rendered `braintree help TOPIC`, the installed `check` and `feedback` paths,
the unchanged semantic default/override/empty cases, and idempotence.

Evidence: `sh tests/install.sh` printed `install tests: passed`; `make test`
printed `All checks passed!`, `Success: no issues found in 51 source files`,
`worktree-parallel: passed`, `install tests: passed`, and `363 passed, 3 skipped`
in pytest; `braintree check` passed after this status move. The README
describes the shared-per-root layout in the Install and Layout sections.
