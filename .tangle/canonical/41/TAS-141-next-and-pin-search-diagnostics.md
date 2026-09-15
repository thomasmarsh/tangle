---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Reject a wikilink inside an action-sentence next by name and prescribe anchored dependency searches.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Hekate `FBK-019` A and B at `0.6.0+g3bacaf5`. Probe: a `next` written as
`Move this node to resolved once [[IDX-001-scratch]] closes.` fails with
`frontier is not a direct child` and the diagnostic names no link, so the
offending link must be found by trial; `SKILL.md` does not say an action sentence
must contain no wikilink. Separately, `references/coordination.md` prescribes
`rg -n -F 'Depends on [[ID]] at context_rev '` and
`references/dependencies.md` prescribes `rg -n -F 'Gated on [[...]]'`; both are
unanchored and match the command text where a node quotes it, so a "zero
consumers" reading requires inspection.

# Outcome

`SKILL.md` states that a `next` written as an action sentence must contain no
wikilink, `tangle check` names the token it treated as the frontier route, and
the dependency references prescribe an anchored search that matches a pin or gate
line rather than a quoted command.

# Done when

- The no-wikilink action-sentence rule is in `SKILL.md` and pinned by a contract
  test.
- The `next-not-direct-child`/`next-resolved-node` diagnostic names the offending
  link or token.
- `references/dependencies.md` and `references/coordination.md` use an anchored
  search form, and the self-match hazard is stated.
- Tests cover the diagnostic and the anchored recipe.
- `make test` passes.

# Result

An action-sentence `next` now carries no wikilink, the checker names the token
it treated as the frontier route, and the dependency references search with a
line anchor that skips their own quoted command.

`SKILL.md`'s status/next paragraph adds that a `next` written as an action
sentence must contain no wikilink and that `tangle check` names the token it
treated as the frontier route, extending the accepted-forms sentence that
`tests/test_skill.py`'s `_CORE_INVARIANTS` already pins.

`src/tangle/graph_check.py` splits the frontier verdict. A `next` is now
either a lone `[[direct-child]]` link or an action sentence with no wikilink:
`next-action-wikilink` (new documented code) fires for an action sentence that
embeds a link and names the token, `next-not-direct-child` and
`next-resolved-node` name the route token, and `next-multiple-frontiers` lists
every link it found. The FBK-019 probe
`next: Move this node to resolved once [[IDX-001-scratch]] closes.` now reports
`action-sentence next contains a wikilink: [[IDX-001-scratch]]` instead of a
tokenless `frontier is not a direct child`.

`references/dependencies.md` and `references/coordination.md` replace the
literal `rg -n -F` command-text search with the line-anchored
`rg -n '^Gated on \[\[DEF-auth-protocol\]\]\.'` and
`rg -n '^Depends on \[\[[^]]+\]\] at context_rev [0-9]+\.'` recipes, and state
that the `^` anchor matches an authored pin or gate line rather than the command
text where a node or the reference quotes it, so a zero-consumer reading needs
no inspection instead of forcing one.

Tests: `tests/test_graph_check.py` adds
`test_action_sentence_next_containing_a_wikilink_names_the_token` (the embedded
link is a live direct child, so only the new rule makes it a finding) and
`test_non_child_route_names_the_offending_token`, and the `_MUTATIONS` table
gains `_mut_next_action_wikilink` so `next-action-wikilink` is covered by
`test_every_error_class_emits_a_documented_code` and
`test_documented_codes_cover_every_error_class`; the shared fixture's routing
`next` becomes the lone link `[[TAS-002-child]]`. `tests/test_skill.py` adds
`_NEXT_ACTION_NO_WIKILINK_RULE` with its falsification probe
(`_NEXT_ACTION_NO_WIKILINK_PROBE`) and `_ANCHORED_DEPENDENCY_SEARCH_RULE` with
its probe (`_ANCHORED_DEPENDENCY_SEARCH_PROBE`).

`make test` passes and `tangle check` passes (196 nodes). No benchmark
artifact is touched: `graph_check.py` is not one of the seven observable prompt
files embedded in `benchmark/memory-authority-cases.json`.