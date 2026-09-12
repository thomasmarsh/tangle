---
context_rev: 1
priority: P2
updated: 2026-09-12T21:57:26Z
summary: Give a client a one-command path to create a routed, correctly-stamped node of any type, the way feedback record already does for FBK.
---

# Context

Parent [[TAS-095-usage-feedback-hardening-round-four]].

Admitted from the portfolio gap map in
[[THO-013-round-four-usage-feedback-and-portfolio-analysis]]. Five of the nine
targeted client use-cases are capture-shaped (brainstorming, detailed planning,
deliberation, capturing errand thoughts, and recording architectural
decisions). `braintree feedback record` already creates a routed,
revision-stamped node from three flags in one step, but it is the only command
that creates a node; there is no equivalent for `THO`, `DEF`, `DEC`, or `TAS`.
Capturing one by hand costs `braintree allocate PREFIX`, a read of
`index-map.md` for the hub route, hand-authored `context_rev`, `updated`,
`summary`, and `next` frontmatter, a chosen status directory, and a
`braintree check nodes` pass.

# Outcome

A client captures a durable decision, question, definition, or work item as a
routed, correctly-stamped node in one documented step, with the id, route,
timestamp, and required frontmatter supplied by the command instead of
hand-authored.

# Done when

- One command creates a node of a named type from a summary and body, allocating the next id from Markdown and discovering the primary route to the vault's root hub the way `feedback record` does.
- The created node carries a positive `context_rev` and a current `updated`, and lands in the status directory the caller names so `braintree check nodes` accepts it.
- The admission threshold is unchanged: the command creates what the caller has already decided to admit rather than admitting notes with no foreseeable action value.
- A test creates one node of each of `THO`, `DEF`, `DEC`, and `TAS` through the documented path and confirms the checker accepts them, and `make test` passes.

# Result

The capture path is a new recording verb beside `feedback record`, not an
extension of `allocate`: the `Done when` requires allocation from Markdown, and
`allocate` stays the sidecar reservation of `PREFIX-NNN`. `braintree node
record` creates one routed, correctly-stamped node of a named type from a
summary and body:

```sh
braintree node record --type THO --summary 'A question.' --body 'The body.'
```

`--type` is one of `THO`, `DEF`, `DEC`, or `TAS`; `--status` names the status
directory and defaults to `proposed`; a `TAS` node in an unfinished status
requires `--next` carrying its one action and a `resolved` node must omit it;
a `blocked` body must carry the `# Blocked` section the checker requires.
`--nodes`, `--route`, `--id`, `--summary`, and `--slug` override the vault,
the discovered route, the allocated id, the derived summary, and the derived
slug, as they do for `feedback record`. `FBK` stays with `braintree feedback
record`, and a root `IDX` hub is declared in `index-map.md`, so neither is a
capture target here.

The authored primitive is `src/braintree/node_record.py`: it holds the one
spelling of Markdown id allocation, root-hub route discovery, route
normalization, slugging, and the non-clobbering write, and
`src/braintree/feedback_record.py` now imports them instead of carrying its own
copies, so the two capture paths cannot drift. `src/braintree/main.py`
dispatches `node record` beside `feedback record`; a bare `node NODE` view is
unchanged. `SKILL.md` documents the capture path under `## Capturing a node`
and restates that the admission threshold is the caller's decision.

Limitations: the command supplies the stamp, not the semantics, so a `--next`
that does not name a direct child can still produce a node the checker rejects.
`--body` is one argument, so a multi-paragraph body is passed with shell
quoting, and `priority` plus dependency and `Gated on` edges are not capture
flags. The tests live in `tests/test_feedback_record.py` because this slice's
write set pins that path; they cover both capture writers.

One file outside the write set changed under the coordinator's explicit
sanction: the token-benchmark fixture copies every file in `src/braintree` and
pins the resulting count, so the new module moves that derived pin in
`tests/test_token_benchmark.py` from 74 to 75. No other assertion changed.

Evidence:

- `tests/test_feedback_record.py` creates one `THO`, `DEF`, `DEC`, and `TAS`
  node through the documented path and `graph-check` accepts the result; it also
  covers dispatch through the unified command, id allocation from Markdown,
  the `--next`, `--status`, `--id`, `--route`, `--slug`, and `--body` rules,
  and every error path. The existing `feedback record` suite still passes over
  the shared primitives.
- `tests/test_skill.py` pins the documented capture contract.
- `braintree check nodes` and `make test` pass.

