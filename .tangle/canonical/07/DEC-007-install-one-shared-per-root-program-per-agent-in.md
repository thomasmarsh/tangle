---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Install one shared per-root program; per-agent installs copy only skill prose.
---

Area [[IDX-001-execution-graph]].

# Context

Depends on [[DEF-001-distribution-contract]] at context_rev 1.

Depends on [[TAS-065-language-agnostic-braintree-command]] at context_rev 1.

The single `tangle` command is generated at `<root>/.local/bin/tangle` and
bakes the destination of the install that wrote it. The launcher is per root but
its target is per agent (`~/.agents/skills/...`, `~/.claude/skills/...`,
`~/.pi/agent/skills/...`), so installing one agent silently repoints the shared
command away from another agent's copy. Each agent also carries a full source
copy and builds its own dependency environment, so the same program is installed
and built once per agent.

# Decision

Separate the installed program from per-agent skill discovery. Install the
Tangle program once per root at a stable program location and point
`<root>/.local/bin/tangle` at that location, so reinstalling any agent skill
never rewrites the command's target. Each agent install copies only the skill
prose it discovers (`SKILL.md`, `references/`, and agent metadata) into its own
destination; it does not carry or build a second program.

# Rationale

The single documented command is required and stays. The defect is that a
per-root launcher targets a per-agent destination, so install order decides
which copy runs. One stable per-root target removes the conflict by construction
and reduces N dependency environments to one, while every documented invocation
stays free of the toolchain. Installation remains a local copy from the checkout
rather than a package-manager dependency, so [[DEC-005-reinstall-not-migration]]
still holds.

# Consequences

The installer maintains the shared program once per root; agent installs become
small prose copies. `tests/install.sh` must prove that installing one agent does
not change the launcher target or the shared program revision. The shared
program is one failure domain: removing it breaks every agent's command,
recovered by reinstalling. Installed prose and the shared program can drift in
revision, so the implementing task must define the compatibility check and how
the installer updates both. The `--semantic` extra and its zero-config provider
default live with the shared program. This revises the per-agent full-copy model
of [[TAS-038-uv-scaffold-and-distribution-contract]] and the target wiring of
[[TAS-065-language-agnostic-braintree-command]] without superseding either.
