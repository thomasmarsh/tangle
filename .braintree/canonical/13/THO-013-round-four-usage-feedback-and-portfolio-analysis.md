---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Round-four Tangle feedback disposes FBK-001 and FBK-002 as fixed and admits FBK-003 and FBK-004 plus one portfolio gap in one-command node capture.
---

# Question

Area [[IDX-001-execution-graph]].

`braintree feedback scan /Users/thomasmarsh/git/tangle` reports four proposed
feedback nodes after the round analyzed in
[[THO-011-round-three-usage-feedback-analysis]]: `FBK-001` through `FBK-004`.
`FBK-001` and `FBK-002` are the round-three findings N8 and N5, still open in
the consuming vault. Which findings still hold against this implementation at
`0.5.0`, and which of the nine targeted client use-cases lack a capability that
removes a reasoning step or a round trip?

# Conclusion

Reproduction used an isolated probe vault at `/tmp/bt-r4` with
`BT_SIDECAR_DIR`/`BT_PROJECT_ID`, so no reservation state and no vault state
was disturbed.

| Feedback | Scan revision | Verdict | Evidence |
|----------|---------------|---------|----------|
| `FBK-001` | `0.5.0+gc99a080` | fixed, disposed | An unpinned `Gated on [[TAS-001-probe]].` line to a proposed target passes the checker (`graph check: passed (3 nodes)`), [[TAS-086-unresolved-dependency-representation]] states the form, and an unpinned `Depends on` to the same target fails with `a not-yet-resolved predecessor is recorded as Gated on [[TAS-001-probe]].` |
| `FBK-002` | `0.5.0+gc99a080` | fixed, disposed | `braintree hash nodes/proposed/TAS-001-probe.md` now fails with `help: "Use the bare ID 'TAS-001' or the full node name 'TAS-001-probe', not a path."`, the bare ID and stem both succeed, and [[TAS-085-hash-addressing-and-operand]] states the accepted forms and the frontier-transition ordering. |
| `FBK-003` | `0.5.0+g64359e6` | open, admitted | No `SKILL.md` text matches `primitive`, `seam`, or an in-scope-authoring rule; the parallel-worktree contract names the write set but not whether a gate's needed primitive may be authored inside it. |
| `FBK-004` | `0.5.0+g64359e6` | open, admitted | `braintree claim TAS-001-probe worker --base-hash "$(braintree hash TAS-001-probe)"` printed `result: "claimed"` and echoed the two-line `node:`/`content_hash:` block as the recorded `base_hash`; the bare digest the skill mandates then failed on release, non-zero, forcing a release-and-reclaim once the mistake was noticed. |

Neither defect re-admitted from `FBK-001` or `FBK-002`: both were already fixed
by the round-three children, and re-admitting fixed friction would be node
churn.

## Portfolio gap map

One gap is admitted. The rest are covered or deliberately excluded by the
existing contract, and that is stated here instead of becoming work.

| Use-case | Coverage | Verdict |
|----------|----------|---------|
| Brainstorming | The admission threshold decides whether an idea becomes a node; a question worth answering is a `THO`, and a candidate work item is a `proposed` child. | disposed: the missing piece is the capture cost, which the admitted gap covers, not a new status or type |
| Detailed planning | A user-requested plan pre-creates children as `proposed`, the parent `next` names one frontier child, `frontier --group` clusters advisory workstreams, and `node` plus `Parent` backlinks show the tree. | disposed, covered |
| Choosing work items | `frontier`, `next --rank`, and `orient` answer directly, and a coordinating parent's `next` route resolves the candidate list. | disposed, covered |
| Prioritization | `next --rank` orders unfinished work by `priority` (`P0`-`P3` asc, transitive blocking desc, `updated` desc, `id` asc) and `search --priority P` refines a lexical query; the documented `find`/`rg` recipe covers filter-only enumeration. | disposed, covered |
| Establishing risk boundaries | `blocked` records missing input or approval, `check` enforces graph invariants, and the coordinator's write set bounds a slice. The unstated slice-scope boundary is `FBK-003`. | admitted via [[TAS-097-slice-primitive-scope]] |
| Deliberating about work | A `THO` node holds Question, Hypothesis, Prediction, Test, and Evidence. | disposed, covered; authoring cost is the admitted gap |
| Maintaining work logs | The admission contract deliberately excludes routine narration and tool-call logs, and Git history plus a node's `# Result` is the sanctioned log. | disposed: a log node is the transcript the model rejects |
| Capturing errand thoughts | `braintree feedback record` creates a routed, revision-stamped node in one step, but no equivalent exists for `THO`, `DEF`, `DEC`, or `TAS`. | admitted via [[TAS-098-node-capture-path]] |
| Recording architectural decisions | The `DEC` type with Decision, Rationale, and Consequences is current knowledge once resolved. | disposed, covered; creation cost is the admitted gap |

The admitted capture gap is measured, not asserted. `braintree --help` lists 22
commands and `feedback record` is the only one that creates a node; capturing a
question, a decision, or a work item by hand costs `braintree allocate PREFIX`,
a read of `index-map.md` for the hub route, hand-authored `context_rev`,
`updated`, `summary`, and `next` frontmatter, a chosen status directory, and a
`braintree check nodes` pass, where the same act for an `FBK` node is one
command.

# Decision

Create the coordinating task [[TAS-095-usage-feedback-hardening-round-four]]
with one child per independently resumable confirmed change:

- [[TAS-096-base-hash-validation]] — `FBK-004`.
- [[TAS-097-slice-primitive-scope]] — `FBK-003` and the risk-boundary use case.
- [[TAS-098-node-capture-path]] — the one admitted portfolio gap.

Round four is lower severity than rounds two and three: no finding prevents a
worker from coordinating or from claiming correctly once it notices the bad
operand, so the coordinating task is `P2` and does not displace the `P1`
frontier routed by [[TAS-087-off-the-shelf-embedding-and-clustering]].
