---
context_rev: 1
updated: 2026-09-13T14:59:19Z
summary: Round-seven Tangle feedback confirms nine independently resumable changes across premise correction, resolved-child completion, allocation visibility, next/search diagnostics, handoff artifact naming, definition completeness, derived artifacts, session slices, and summary integrity.
---

# Question

Area [[IDX-001-execution-graph]].

`braintree feedback scan /Users/thomasmarsh/git/tangle` reports ten proposed
feedback nodes recorded after the round analyzed in
[[THO-017-round-six-usage-feedback-analysis]]: Tangle `FBK-016` through Tangle
`FBK-025`, recorded at `0.6.0+g3bacaf5`. The ids collide with this vault's own
`FBK` numbering, so they are cited as Tangle `FBK-0NN`. Which findings still hold
against this implementation at `0.6.0+g3bacaf5`, which are duplicates or already
handled, and what self-improvement work do they require?

# Conclusion

Reproduction used the isolated scratch vault `/tmp/bt-r7` with
`BT_SIDECAR_DIR`/`BT_PROJECT_ID`, so no reservation state and no vault state was
disturbed, plus exact searches of `SKILL.md`, `references/`, and `src/`.

| Feedback | Scan revision | Verdict | Evidence |
|----------|---------------|---------|----------|
| Tangle `FBK-016` | `0.6.0+g3bacaf5` | open, admitted | `rg -in premise SKILL.md references/ src/` matches nothing: no rule for a claimed node whose recorded premise or `# Outcome` is factually wrong, nor for whether that correction bumps `context_rev`. |
| Tangle `FBK-017` | `0.6.0+g3bacaf5` | open residual, admitted | Round six [[TAS-115-parent-next-advance-ownership]] already added `next-resolved-node` and the coordinator-owns-the-advance rule (`references/coordination.md`), so detection and ownership are handled. The unhandled residual is the worker's completion path while the gate is red and the checker cannot distinguish the normal multi-writer transient from a genuine stale route. |
| Tangle `FBK-018` finding 1 | `0.6.0+g3bacaf5` | disposed, out of scope | A mid-session installed-tool upgrade invalidating already-issued worker path handoffs is a harness/session concern, not a Braintree contract; carrying the version into handoffs is the coordinator's brief, not a graph rule. |
| Tangle `FBK-018` finding 2 | `0.6.0+g3bacaf5` | open, admitted | `braintree allocate` burns an id permanently when the caller discards it and no contract states it; `braintree status` prints only `prefix,next` (`reservations[1]{prefix,next}`), so reserved-but-unwritten ids are not inspectable. |
| Tangle `FBK-019` A | `0.6.0+g3bacaf5` | open, admitted | Probe: `next: Move this node to resolved once [[IDX-001-scratch]] closes.` fails with `frontier is not a direct child` and names no link. `SKILL.md` says a `next` is "a plain action sentence ... or a single `[[direct-child]]` link" but never says an action sentence must contain no wikilink. |
| Tangle `FBK-019` B | `0.6.0+g3bacaf5` | open, admitted | `references/coordination.md` prescribes `rg -n -F 'Depends on [[ID]] at context_rev '` and `references/dependencies.md` prescribes `rg -n -F 'Gated on [[...]]'`; both are unanchored, so a node that quotes the command is a self-match and a "zero consumers" reading requires inspection. |
| Tangle `FBK-020` | `0.6.0+g3bacaf5` | open, admitted | A handoff ordered reuse of an "existing experiment-spec format" that exists nowhere in the repo or nodes; the coordination reference has no rule that a handoff names the concrete artifact it orders reused, so the worker invented the artifact and its shape. |
| Tangle `FBK-021` | `0.6.0+g3bacaf5` | open, admitted | A resolved `DEF` deferred a consumer-visible aggregation-shape vocabulary to the implementing task, which invented slice families, a zero-versus-not-observed rule, and a metric-key spelling with no versioned coverage; `SKILL.md` and the references give no definition-completeness rule for a shape consumers must author. |
| Tangle `FBK-022` | `0.6.0+g3bacaf5` | open, admitted | `rg -in 'derived artifact\|regenerat' SKILL.md references/` matches nothing: no rule for who regenerates a resolved node's derived artifacts when a later node's fix invalidates them, or how that regeneration is reported. |
| Tangle `FBK-023` finding 1 | `0.6.0+g3bacaf5` | open, feeds [[THO-019-advisory-size-and-effort-hints]] | A prescribed slice plan bundled several independently verifiable deliverables per letter; this is direct field evidence for a node-level size signal and is routed to the advisory-hints question rather than a hardening leaf. |
| Tangle `FBK-023` finding 2 | `0.6.0+g3bacaf5` | disposed, out of scope | The async run wrapper's 30-minute wall clock and stale needs-attention state are harness behavior (`pi-subagents`), not Braintree commands or contract. |
| Tangle `FBK-023` finding 3 | `0.6.0+g3bacaf5` | open residual, merged into the `FBK-017` child | Folding the parent-next advance into the resolving worker's commit when the write set names the parent is already allowed by [[TAS-115-parent-next-advance-ownership]]; the remaining round-trip reduction is the same completion-path change as Tangle `FBK-017`. |
| Tangle `FBK-024` | `0.6.0+g3bacaf5` | open, admitted | `SKILL.md` says one node may span sessions but never sizes a session to a coherent slice, and it says never bump `context_rev` for a status move without stating whether a `blocked`->`proposed` move that flips downstream-start context is a status move or a semantic change. |
| Tangle `FBK-025` finding 1 | `0.6.0+g3bacaf5` | open, admitted | Probe: `braintree node record --summary <200 chars>` exited `0` and stored `summary: This summary is deliberately much longer than ninety-six characters so that a truncation becomes` (cut mid-phrase at 96 characters); `_SUMMARY_LIMIT = 96` in `node_record.py` trims silently and `authoring.md` documents no limit. |
| Tangle `FBK-025` finding 2 | `0.6.0+g3bacaf5` | open, merged into the `FBK-018` child | Same allocation-visibility outcome: an id reserved and never written is indistinguishable from a missing node, and `braintree allocate TAS` skipped 053-056 with no listed reservation. |

Disposed without admission:

- Tangle `FBK-018` finding 1 and Tangle `FBK-023` finding 2 are harness or
  session concerns, not Braintree contract; re-admitting them would add nodes
  this repository cannot resolve.
- Tangle `FBK-023` finding 1 is not a hardening leaf: it is the strongest
  evidence for the advisory-hints design and is cited by
  [[THO-019-advisory-size-and-effort-hints]].
- Tangle `FBK-023` finding 3 is the same completion-path outcome as Tangle
  `FBK-017` and is merged rather than duplicated.
- Tangle `FBK-025` finding 2 is the same allocation-visibility outcome as Tangle
  `FBK-018` finding 2 and is merged.

# Decision

Create the coordinating task
[[TAS-137-usage-feedback-hardening-round-seven]] with one child per
independently resumable confirmed change:

- [[TAS-138-premise-correction-rule]] - Tangle `FBK-016`.
- [[TAS-139-resolved-child-completion-path]] - Tangle `FBK-017` and `FBK-023` finding 3.
- [[TAS-140-allocation-lifecycle-visibility]] - Tangle `FBK-018` finding 2 and `FBK-025` finding 2.
- [[TAS-141-next-and-pin-search-diagnostics]] - Tangle `FBK-019` A and B.
- [[TAS-142-handoff-names-referenced-artifacts]] - Tangle `FBK-020`.
- [[TAS-143-definition-completeness-for-deferred-shapes]] - Tangle `FBK-021`.
- [[TAS-144-derived-artifact-regeneration-ownership]] - Tangle `FBK-022`.
- [[TAS-145-session-slice-and-blocker-revision]] - Tangle `FBK-024`.
- [[TAS-146-summary-truncation-integrity]] - Tangle `FBK-025` finding 1.

Round seven is `P2`. Most findings are contract-clarity rules; the two behavior
changes are the allocation/reporting visibility and the summary-length guard, and
neither blocks coordination. The round does not displace the `P1` agent-memory
evaluation frontier routed by [[TAS-120-agent-memory-evaluation-program]].
