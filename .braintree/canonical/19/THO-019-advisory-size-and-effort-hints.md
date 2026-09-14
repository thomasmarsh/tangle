---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Reject advisory size and effort hints; the durable-outcome boundary already governs slice size and no node-level capability consumer exists.
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

# Result

**Rejected.** No advisory `size:` or capability/effort field is added to node
frontmatter. The open question was authority and value, not mechanics, and
neither is established; the friction that motivated the question is already
governed by the landed durable-outcome boundary.

**Test 1 — one hint or two, and is size redundant with `# Done when` count?**
Neither is worth carrying, so the one-versus-two split is moot. When they would
apply the two concerns are independent (size is not derivable from required
capability, nor the reverse), so one token could not cover both. `# Done when`
bullet count is not a size proxy in either direction: across this vault,
coordinating nodes with comparable child counts range from 0 to 11 Done-when
bullets (TAS-121, 9 children / 5 bullets; TAS-037, 5 children / 0 bullets;
TAS-111, 8 children / 10 bullets), and a leaf task such as this node carries no
`# Done when` at all. The motivating case is decisive: in Tangle Increment 6 the
two children the user flagged as excessively large (TAS-048 and TAS-049 under
TAS-045) carried 7 and 5 Done-when bullets while the accepted slices carried 7,
6, and 4 — the count did not separate them. Done-when measures acceptance
completeness, not effort, so a size hint is neither redundant with it nor
recoverable from it.

**Test 2 — schema, values, `node record`, `frontier`/`next --rank`.** Recorded
for a future reopening only, since the resolution rejects adoption: the
frontmatter parser already tolerates arbitrary extra flat scalars, so `size:` and
`effort:` need no schema migration
(`_parse_frontmatter("context_rev: 1\nsize: M\neffort: high\n...")` returns both
keys). `braintree node record --help` exposes no size or capability flag, and
`braintree frontier` and `braintree next --rank` surface only
`id,status,priority,summary,next` (plus `stale`/`blocking`), so surfacing a hint
would need new output fields. Mechanics were never the blocker.

**Test 3 — failure modes.** (a) A size hint recreates the per-node sizing ritual
the contract rejects: [[THO-015-how-should-braintree-correct-task-granularity-wi]]
concluded boundary reassessment is event-triggered, and
[[TAS-104-state-event-triggered-split-and-consolidation-ev]] landed the rule that
"a node owns one durable outcome or decision, not an estimated session, commit,
agent assignment, or amount of code." A coarse size token *is* an estimated
amount of work and re-encodes the boundary the contract forbids. It also cannot
be verified — `braintree check` can validate a token, never its truth — so it
would be an unbacked advisory an agent could mistake for authority. (b) A stale
effort tier misdirects model selection: the tier is fixed at authoring time while
the task's real difficulty changes during execution, and a wrong coarse token is
worse than the full node body (Outcome, Done when, Context, dependencies) the
coordinator already reads.

**Why the cited field evidence does not adopt the hint.** Tangle `FBK-023`
finding 1 records prescribed *slice nodes* (TAS-046 through TAS-050 under TAS-045)
that bundled several independently verifiable deliverables each. But the
coordinator that prescribed each slice authored both its deliverable/`# Done
when` list and any would-be `size:` token, so the hint would be redundant with
the coordinator's own already-written list and could not prevent the bundling.
The observed remedy is the durable-outcome split rule already landed by TAS-104
from THO-015 — split when a node carries another outcome that can be accepted,
verified, or resumed independently. `FBK-023`'s own improvement asks to "size
each prescribed slice as one durable outcome", which is that rule, not a metadata
field. The delegation direction ([[TAS-136-pilot-separability-audit]] and the
evaluation program) records `requested_model` and `requested_reasoning_effort` per
run as post-hoc experiment provenance, not a signal a producer stamps on a node
before a run; this node's own Context concedes that direction "has no feedback
yet." Admitting a field on that basis is speculative scaffolding with no decision
it changes.

**Reopening evidence.** Reopen only with: a feedback node showing a coordinator
that already held the durable-outcome rule and still repeatedly mis-sized
prescribed slices, such that a stated size token would have changed the split; or
a delegation trace where a node-level capability signal changed an assignment
and outperformed coordinator judgment from the node body; or evidence that a
consumer selects model or effort from node metadata rather than full task
context.

# Decision

Rejected — no advisory `size:` or capability/effort field is admitted, and no
implementation follow-on node is warranted: the decision produces no independent
outcome to resume, and the routed evidence (Tangle `FBK-023` finding 1) is already
governed by the landed durable-outcome boundary. This answers the routing in
[[THO-021-round-seven-usage-feedback-analysis]] as "no hardening leaf." The node
resolves to `resolved` with `context_rev` unchanged; it has no pinned consumer.
