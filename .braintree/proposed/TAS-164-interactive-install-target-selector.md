---
context_rev: 1
priority: P2
updated: 2026-09-13T21:49:10Z
summary: Make bare scripts/install.sh interactively discover and multi-select potential install targets instead of demanding explicit agent and destination flags.
next: Make bare scripts/install.sh interactively discover and multi-select potential install targets.
---

# Context

Parent [[TAS-161-routine-interaction-zero-ceremony]].

`scripts/install.sh` requires `(--codex | --claude | --pi)` and `(--project DIR |
--home DIR)` on every invocation, so the caller must already know the agent and
the destination; `scripts/install-claude.sh` removes only the agent flag. Nothing
discovers candidate roots or offers a choice.

# Outcome

Running `scripts/install.sh` with no target arguments interactively presents the
potential install targets — detected project roots and home roots crossed with
the supported agents — as a multi-select and installs each selected target, while
the existing explicit flags remain for non-interactive and scripted use.

# Done when

- Bare `scripts/install.sh` presents a multi-select of discovered install
  targets.
- Selecting several targets installs each one.
- The existing explicit flags and `--dry-run` remain supported.
- Non-interactive invocation without a discoverable target fails clearly instead
  of hanging.
- Tests cover target discovery, the multi-select path, and the non-interactive
  path.
- `make test` passes.
