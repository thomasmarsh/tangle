---
context_rev: 1
updated: 2026-09-13T00:28:43Z
summary: Refactor Braintree into a concise core skill with progressively disclosed references.
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

# Result

Landed the concise core, the canonical reference tree, bounded command help, installer
reference copying, and the restructured contract tests.

## Core, references, and size

`SKILL.md` keeps only first-action safety: Markdown/sidecar authority, vault shape,
admission, the [[TAS-104-state-event-triggered-split-and-consolidation-ev]] durable-outcome rule, status and
lifecycle meaning, canonical edges, reachability, dependency readiness, mutation rules,
the read-and-execute loop, and one routing instruction to load a reference before a
conditional workflow. Conditional detail moved verbatim into three canonical installed
references that the command renders instead of duplicating their text in Python.

Static size (bytes):

| Surface | Before | After |
|---|---:|---:|
| `SKILL.md` (measured `wc -c` at start) | 30,244 | 11,618 |
| `references/coordination.md` | — | 8,086 |
| `references/dependencies.md` | — | 3,443 |
| `references/authoring.md` | — | 9,036 |
| references total | — | 20,565 |
| core + references | — | 32,183 |

The core is 61.6% smaller than the measured pre-split file and below the 13,481-byte
compact baseline [[DEC-004-compact-skill-text]] adopted. The reference total is larger
than the core by design: it is loaded only per conditional workflow. The measured
skill now includes the reference tree, so `token_benchmark._installed_skill_files` and
the pinned fixture count (75 to 79) were updated together to keep the fixture an exact
install mirror.

## Command help

- `braintree --help` stays the short command and topic index (29 command rows plus a
  `topics[3]` table), well under the 8 KB the test bounds it to.
- Every public verb accepts `--help` and answers with bounded TOON: `usage`, `purpose`,
  `arguments[]`, `outputs[]`, `exits[3]` (`0`/`1`/`2`), and `hazards[]`, then the topic
  pointer. Coverage is asserted for 36 verb spellings across `main.py` and `cli.py`.
- `braintree help TOPIC` for `coordination`, `dependencies`, and `authoring` prints the
  installed Markdown file's bytes unchanged, needs no vault, and never initializes the
  sidecar; `braintree help` lists the topics and `braintree help bogus` exits 2 naming
  them.
- Diagnostics point at narrow help: `main._usage_error` and `cli._usage_error` emit
  ``Run `braintree <verb> --help` for operands and exit meanings`` when a command is in
  scope, and the global pointer only for an unknown top-level command.

## Installers and tests

`scripts/install.sh` copies `references/*.md` beside `SKILL.md`; `scripts/install-claude.sh`
inherits it; the pi path is the same generic installer. A reference-only edit is detected
(`result: "installed"` and the file restored) and the next run returns `result: "no-op"`.
`tests/install.sh` compares the copied reference tree for every destination, renders each
topic from the installed command in a vault-free working directory, and proves the
reference-only drift and no-op behavior; `tests/test_launchers.py` asserts the same
file-for-file topic rendering through the dev launcher.

`tests/test_skill.py` was restructured: it keeps the literal grammar the checker and
clients depend on (status directories, `Parent`/`Area`, the pin and gate forms,
`Superseded by`, frontmatter keys, `Refs:`, `braintree_revision:`) and the core routing
and durable-outcome invariants, and replaces the broad prose-fragment locks with
observable routing and behavioral invariants: a topic loads as its installed bytes, every
public verb `--help` exits 0 and names its outputs and exit codes, `braintree --help`
stays a bounded index, the core stays under the size bound, and the installed surfaces
still hide the implementation.

## Evidence

- `braintree check nodes` -> `graph check: passed (128 nodes)`.
- `make test` -> ruff, strict mypy, 435 passed / 3 skipped, `tests/install.sh` and
  `tests/worktree-parallel.sh` pass, `git diff --check` clean.
- `braintree benchmark verbs --verify` -> all seven direct-answer verb gates pass,
  `verification: passed` (zero live model calls).
- `braintree benchmark behavioral --verify` -> both filesystem diagnostics pass,
  `verification: passed` (zero live model calls).
- [[THO-016-has-cumulative-contract-growth-invalidated-the-c]] was verified `resolved`
  at `context_rev: 1` before this work and is the pinned dependency this node discharged.

## Limitations

- No live token A/B was run; the correctness evidence is the zero-live harnesses plus
  static size, per the no-live-spend constraint. A matched live A/B remains available
  through the existing staged harness when an owner authorizes spend.
- The core was compacted by moving, not dropping, prose; the combined installed surface
  is larger than the pre-split file, so a cold agent that loads all three references
  reads more than before. Routing keeps that conditional.
