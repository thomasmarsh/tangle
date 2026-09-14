---
status: resolved
context_rev: 3
updated: 2026-09-14T23:40:13Z
summary: Provide a dedicated Claude Code installer with a wrapper-valid interface and shared core installation logic.
---

# Parent

Parent [[TAS-001-distribution]].

# Context

Depends on [[TAS-006-help-contract]] at context_rev 1.

# Outcome

Provide a dedicated Claude Code installer entry point while preserving the core installer's structured behavior and legacy Claude flag.

# Done when

`scripts/install-claude.sh` delegates to `scripts/install.sh`, supports explicit project or personal targets and wrapper-valid help, dry-run, version, TOON, no-op, and error contracts, and has temporary-directory tests and concise README documentation. `scripts/install.sh --claude` remains supported, and Claude installation adds no Codex-only agents metadata.

# Result

Added the executable thin Claude wrapper over `scripts/install.sh`; its presentation mode supplies only wrapper-valid help and usage corrections while the core retains the sole copy implementation and generic `--claude` compatibility. Temporary-directory tests verify project/home installs, dry runs, exact SKILL/checker bytes, idempotence, no `agents/` metadata, wrapper help, version, and invalid input. `sh tests/install.sh` passed.
