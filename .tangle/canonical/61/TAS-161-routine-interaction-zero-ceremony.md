---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Make routine interaction zero-ceremony: warn on orphaned nodes, maintain the index invisibly, and install through an interactive target multi-select.
---

# Context

Area [[IDX-001-execution-graph]].

Maintainer-directed interaction-surface work, independent of the Hekate feedback
analyzed in [[THO-022-round-eight-usage-feedback-analysis]]. Three observed
ceremonies: an orphaned unfinished node is reported only by `tangle check` and
not by the direct-answer verbs a client actually calls; clients are taught to run
`tangle index` and to reason about a SQLite sidecar that should be a private
implementation detail; and `scripts/install.sh` requires the caller to name the
agent and the destination explicitly.

# Outcome

Routine Tangle interaction is self-maintaining and self-reporting: orphaned
nodes surface as a loud warning on every interaction, the derived index
maintains itself as a private implementation detail, and install discovers and
offers its targets interactively.

# Done when

- Every direct-answer interaction warns on orphaned unfinished nodes.
- The index is maintained automatically on all interactions and SQLite is no
  longer named as a client concept in `SKILL.md` or `references/`.
- Bare `scripts/install.sh` interactively offers potential install targets as a
  multi-select.
- Every child is resolved or disposed with rationale.
- `make test` passes.

# Children

- [[TAS-162-orphan-warning-on-every-interaction]]
- [[TAS-163-amortized-transparent-index]]
- [[TAS-164-interactive-install-target-selector]]

# Result

Resolved: all three children are resolved with evidence, so every `Done when`
criterion holds. [[TAS-162-orphan-warning-on-every-interaction]] made the four
direct-answer verbs (`frontier`, `next`, `orient`, `status`) warn on each orphan
unfinished node on stderr without changing stdout or the exit code.
[[TAS-163-amortized-transparent-index]] made the derived index maintain itself
after every dispatched interaction and removed SQLite and the sidecar from
`SKILL.md` and `references/` as client concepts, leaving `tangle index` as
explicit repair only. [[TAS-164-interactive-install-target-selector]] made a bare
`scripts/install.sh` discover the enclosing project root and the home root,
cross them with `codex`/`claude`/`pi`, and install every target chosen from a
numbered multi-select, while the explicit flags stay the non-interactive
contract.

Gates: `tangle check` passed (197 nodes); `tangle benchmark verbs --verify`
passed; `make test` passed (719 passed, 3 skipped, 79 deselected). Each child
carries its own tests and evidence, and no child was disposed without a
resolution.
