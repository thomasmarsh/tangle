---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Stop the checker from parsing wikilink-shaped tokens inside inline code spans and fenced code blocks as real links.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N4: the checker scans raw node text, so a node that quotes the skill's own
grammar in code font or a fenced block produces a spurious `broken link`
finding. This is a recurrence of the round-two source `Tangle THO-008 F2`; the
current workaround is to never reproduce a link-shaped token in any node text.

# Outcome

Quoting a wikilink-shaped token in code is not a graph error, while real
wikilinks remain validated.

# Done when

- Inline code spans and fenced code blocks are excluded from link scanning.
- A quoted token in code produces no `node-broken-link` finding, and a real wikilink beside it still validates.
- Regression tests cover inline and fenced forms and `make test` passes.

# Result

The node allowed no documentation-only branch: the checker had no code masking
at all, so a quoted token in code was indistinguishable from a real link. The
fix masks Markdown code before the link scan and documents the contract.

`graph_check.py` gains `_mask_code`, which blanks inline code spans and fenced
code blocks while preserving offsets and line breaks, and `_check_links` now
reads the masked copy:

- `_mask_inline_code` blanks a backtick span from its opening run to the next
  run of exactly the opening length, so a shorter or longer run stays literal
  text and an unterminated run does not open a span.
- `_mask_code` tracks a fenced block per line: a `` ``` `` or `~~~` opener with
  at most three leading spaces starts it and a same-character run at least as
  long closes it. Content inside either region becomes spaces.
- Masking is scoped to the link scan that raises `node-broken-link`; the
  context-edge, primary-route, and reciprocal-edge scans still read the node
  text directly.

`SKILL.md` states the contract in the integrity section: link scanning ignores
wikilink-shaped tokens inside inline code spans and fenced code blocks, so a
node can quote the skill's own grammar in code without a false `broken link`
finding.

Evidence:

- `tests/test_graph_check.py` adds `test_inline_code_span_hides_a_link_shaped_token`,
  the `test_fenced_code_block_hides_a_link_shaped_token` case for both `` ``` ``
  and `~~~` fences, and `test_real_link_beside_quoted_tokens_still_fails`, which
  asserts the real broken link is still reported while both quoted tokens are
  silent.
- `tests/test_skill.py` adds `test_skill_code_masking_status`, pinning the
  `SKILL.md` contract text.
- `make test` passes (280 tests) and `braintree check nodes` passes.
