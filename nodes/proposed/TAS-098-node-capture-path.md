---
context_rev: 1
priority: P2
updated: 2026-09-12T17:32:35Z
summary: Give a client a one-command path to create a routed, correctly-stamped node of any type, the way feedback record already does for FBK.
next: Settle whether the capture path is a new recording verb beside feedback record or an extension of allocation, then land it with tests.
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
