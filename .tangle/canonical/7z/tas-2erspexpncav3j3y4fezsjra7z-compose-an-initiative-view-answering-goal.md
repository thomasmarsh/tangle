---
context_rev: 1
priority: P2
status: proposed
updated: 2026-09-15T14:36:52Z
summary: Compose an initiative view answering goal, approach, decisions, and remaining work.
next: Extend views.py with an initiative page assembled from a hub or coordinating node's Outcome/Decision content and its unresolved descendants.
---

Parent [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]].

# Context

`views.py` (landed by [[TAS-204-full-census-indexing-markdown-views]]) already generates deterministic by-status, by-area, by-priority, recent, and external-project pages from the canonical store, but none of them answer, for one initiative: what are we trying to achieve and why; what approach was chosen; which decisions constrain it; what is complete, what remains, and what happens next.

# Outcome

A generated, disposable initiative page composes existing node content -- a hub or coordinating node's Outcome, cited Decisions, and its unresolved descendants' status and next -- into one human-readable overview, without becoming a second authority that can disagree with the graph.

# Done when

- The page is generated the same way the existing views are: disposable, untracked, rebuilt from Markdown, never authoritative, and excluded from node discovery and graph validation.
- It renders for at least one root hub, pulling Outcome/Decision text and the unresolved-descendant frontier by the same primary-link backlink derivation `tangle frontier` already uses, so it cannot desynchronize from the graph it summarizes.
- Tests cover a hub with a mix of resolved and unresolved descendants, a hub with no unresolved work, and byte-for-byte no-op idempotence on an unchanged vault, matching the existing view tests' pattern.
- `tangle check` and `make test` pass.
