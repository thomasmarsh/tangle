---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: Should nodes carry advisory size and effort hints that guide decomposition and delegation without becoming work claims?
---

# Question

Area [[IDX-001-execution-graph]].

Should a task node carry advisory hints about its expected size (for example a
t-shirt size) and about the effort or model tier its execution needs, so an
agent can decide whether to decompose it and how strong a delegate to assign,
without turning those hints into a work claim or a boundary rule?

# Context

`# Focus`, `priority`, and `active` are advisory navigation. `priority` orders
work but says nothing about size or the capability an executor needs. Two
independent consumer decisions are in play:

- Decomposition: a node whose outcome is too large for one delegation should be
  split, and nothing on the node currently flags that before a worker starts.
- Delegation: an orchestrator choosing a stronger or weaker model or reasoning
  effort for a sub-agent has no node-level signal to read.

The current contract deliberately rejects estimated effort, session count, or
amount of code as a node boundary. [[TAS-104-state-event-triggered-split-and-consolidation-ev]]
states the node owns one durable outcome rather than an estimated session or
amount of code, and [[THO-015-how-should-braintree-correct-task-granularity-wi]]
concludes boundary reassessment is evidence-triggered rather than a per-node
sizing ritual. A hint must not recreate that ritual.

Field evidence for a sizing signal is Tangle `FBK-023`: a prescribed slice plan
bundled several independently verifiable deliverables per letter, each ran 20-48
minutes, and the user flagged the slices as excessively large, so the coordinator
had to split them by hand. The delegation direction has no feedback yet, only the
observation that `priority`, `# Focus`, and `active` are not capability signals.
[[TAS-136-pilot-separability-audit]] and the evaluation program already record a
requested model and reasoning effort per run, which is the consumer vocabulary a
node hint would feed. The frontmatter parser tolerates additional flat scalar
keys, so `size:` and an effort/tier field are feasible without a schema
migration; the open question is authority and value, not mechanics.

# Hypothesis

A small optional advisory pair is worth carrying only if it is defined as
non-authoritative: it never sets a node boundary, never substitutes for
`# Done when`, and never fails the graph check beyond validating the token. The
compact form is one coarse ordinal size (for example `S`/`M`/`L`/`XL`) and one
coarse required-capability tier, both optional on tasks, both refreshed only when
execution changes the estimate. A hint is a routing aid for the coordinator, not
a claim the node will take that long or that only one model may run it.

# Test

- Resolve whether one hint or two is enough, and whether a size hint is
  redundant with a coordinating node's `# Done when` count.
- If adopted, fix the frontmatter schema, the allowed values, whether
  `braintree node record` can set them, and whether `braintree frontier` or
  `braintree next --rank` may surface them (advisory only).
- Weigh the failure modes: a size hint recreating the per-node sizing ritual and
  a stale effort hint misdirecting model selection.
- If rejected, record why here and cite the evidence that would reopen it.
