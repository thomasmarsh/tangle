---
context_rev: 1
priority: P2
updated: 2026-09-13T23:10:57Z
summary: Fail or warn on an over-long summary, or truncate on a word boundary with an ellipsis, and document the limit.
---

# Context

Parent [[TAS-137-usage-feedback-hardening-round-seven]].

Tangle `FBK-025` finding 1 at `0.6.0+g3bacaf5`. Probe: `braintree node record`
with a summary longer than 96 characters exited `0` and stored a summary cut
mid-phrase (`...so that a truncation becomes`); `_SUMMARY_LIMIT = 96` in
`node_record.py` applies `[:_SUMMARY_LIMIT]` silently, and `references/authoring.md`
documents no limit, so four stored summaries in a real vault ended mid-sentence.

# Outcome

`braintree node record` and `braintree feedback record` never silently store a
mid-phrase summary: an over-long summary fails or warns, or truncates on a word
boundary with an explicit ellipsis, and the limit is documented in
`references/authoring.md` and printed by the relevant help.

# Done when

- The chosen behavior is implemented for both capture commands.
- The length limit is documented in `references/authoring.md` and surfaced by the
  relevant help.
- Tests cover the boundary and the failure or warning.
- `make test` passes.

# Result

Took the warn-and-truncate branch: an over-long capture summary is cut on a word
boundary with a trailing `...` and reported, so a capture never stores a
mid-phrase summary and never refuses one either. Both write paths now share one
fitting primitive instead of each holding a private limit.

`src/braintree/node_record.py` replaces the private `_SUMMARY_LIMIT = 96` with a
public `SUMMARY_LIMIT = 96` and `fit_summary`, the single spelling
`feedback_record` imports: a value already within the limit is returned
unchanged, and a longer one is cut at the last word boundary that leaves room for
a trailing `...`. Replaying the finding's own phrasing through the command now
stores `...so that a truncation...` (92 characters, and the character after the
cut head is a space) instead of the reported mid-phrase
`...so that a truncation becomes`. `summary_warning` is the one message both
commands print as `warning: "summary exceeds 96 characters; stored the
word-boundary truncation '<summary>'"`, emitted only when the node was written,
so it reports what was actually stored. `feedback_record` drops its own
`_SUMMARY_LIMIT` copy and fits the summary it derives from `--friction`, which is
the default path the finding hit.

Documentation and help: `references/authoring.md` states under `## Capturing a
node` that "`--summary` is one line of at most 96 characters", names the
word-boundary cut with a trailing `...` and the `warning:` line, and the
`## Feedback nodes` paragraph states that the derived summary "obeys the same
96-character limit". `braintree node record --help` reports the limit on the
`--summary` argument plus the `warning` output field and the truncation hazard,
and `braintree feedback record --help` reports the `warning` output field and the
same `96 characters` hazard.

This is not a `graph_check.py` change. The checker already requires only a
non-empty `summary` and owns no length rule; the defect is a capture path that
cut silently, not a length that was stored. A checker length rule would also be
unusable here: 124 of this vault's 198 stored summaries exceed 96 characters,
because hand-authored nodes were never bounded, so a new rule would fail or warn
on most of the graph it validates.

Evidence: `tests/test_feedback_record.py` pins `SUMMARY_LIMIT == 96`, the
boundary (exactly 96 characters is stored unchanged with no `warning`; one
character more is cut on a word boundary), the mid-phrase regression (`so that a
truncation becomes` never appears in the stored value), the warning text naming
the limit and the stored truncation, the `feedback record` derived-summary path,
and both `--help` surfaces carrying `96 characters`. `tests/test_skill.py` pins
`_SUMMARY_LIMIT_RULE` over `references/authoring.md`, with the falsification
probe `_SUMMARY_LIMIT_PROBE_OVERRIDE_ONLY` (the pre-change `--summary` override
bullet, present in `HEAD:references/authoring.md`, whose every rule clause is
missing). `braintree check` -> `graph check: passed (197 nodes)`; `make test` ->
694 passed, 3 skipped, 79 deselected. No dependency is pinned to this node and no
node pins it, so `context_rev` stays at `1`. The parent
[[TAS-137-usage-feedback-hardening-round-seven]] names this node in its write set,
so this change also resolves it as its last child.
