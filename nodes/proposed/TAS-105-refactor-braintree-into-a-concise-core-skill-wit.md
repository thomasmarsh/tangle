---
context_rev: 1
updated: 2026-09-12T23:55:54Z
summary: Refactor Braintree into a concise core skill with progressively disclosed references.
next: Design the canonical topical help resources, then inventory which core clauses must remain always loaded.
---

Area [[IDX-001-execution-graph]].

# Context

Depends on [[THO-016-has-cumulative-contract-growth-invalidated-the-c]] at context_rev 1.

The skill grew from the measured 13,481-byte compact revision to 28,282 bytes. The conclusion keeps one discovery surface and moves conditional detail behind explicit reference routes; separate subskills are rejected for now.

# Outcome

Every supported install exposes one concise Braintree entrypoint that loads the core graph protocol immediately and routes agents to version-matched, focused guidance only when their current operation requires it. The same canonical topical prose is readable as installed Markdown and through the `braintree` command.

# Design

Make the command self-documenting in bounded layers:

- `braintree --help` remains the short command and topic index.
- Every verb accepts `--help` and describes its operands, output fields, exit meanings, and command-specific hazards.
- `braintree help coordination|dependencies|authoring` prints one workflow topic without requiring a vault or initializing the sidecar.
- The installed Markdown reference is the canonical source for each workflow topic; command help renders that resource instead of duplicating prose in Python strings.
- Diagnostics point to the narrow verb or topic help that resolves them rather than the global catalog.

Keep first-action safety and routing in `SKILL.md`: Markdown authority, admission, status meaning, dependency readiness, and the instruction to load a topic before a conditional workflow. Command help cannot protect an action taken before the agent asks for it.

# Done when

- `SKILL.md` retains the core authority, navigation, admission, outcome-boundary, lifecycle, and mutation invariants while routing conditional coordination, dependency, and authoring detail to focused references.
- Codex, Claude Code, and pi installers copy the reference tree, detect reference-only changes, and retain correct no-op behavior.
- Command syntax is owned by per-verb help, and workflow prose is owned by canonical topical resources exposed both as installed Markdown and `braintree help TOPIC`; `SKILL.md` does not duplicate either where a routing sentence is sufficient.
- Help is bounded, read-only, available without sidecar initialization, version-matched to the installed command, and covered for every public verb and topic.
- Contract tests preserve required literal grammar but replace general prose-fragment locks with observable routing and behavioral invariants.
- Static size evidence and the sanctioned correctness/token evaluation compare the result with the compact baseline; no live model spend occurs without owner authorization.
- `braintree check nodes` and `make test` pass.
