---
context_rev: 1
priority: P2
updated: 2026-09-13T23:23:54Z
summary: Make routine interaction zero-ceremony: warn on orphaned nodes, maintain the index invisibly, and install through an interactive target multi-select.
next: "[[TAS-163-amortized-transparent-index]]"
---

# Context

Area [[IDX-001-execution-graph]].

Maintainer-directed interaction-surface work, independent of the Tangle feedback
analyzed in [[THO-022-round-eight-usage-feedback-analysis]]. Three observed
ceremonies: an orphaned unfinished node is reported only by `braintree check` and
not by the direct-answer verbs a client actually calls; clients are taught to run
`braintree index` and to reason about a SQLite sidecar that should be a private
implementation detail; and `scripts/install.sh` requires the caller to name the
agent and the destination explicitly.

# Outcome

Routine Braintree interaction is self-maintaining and self-reporting: orphaned
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
