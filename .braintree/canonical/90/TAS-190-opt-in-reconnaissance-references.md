---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Cite shared reconnaissance with a non-pinned Informed by relation and read it one hop at a time.
---

Parent [[TAS-189-usage-feedback-hardening-round-eleven]].

# Context

Tangle `FBK-032` finding 5 identifies two separate concerns. The load-band and size-command concern remains owned by [[THO-024-whether-node-files-need-a-bounded-load-band-with]]. This node owns only the missing capability for a work node to cite reusable `THO` reconnaissance without turning that context into a pinned dependency or copying it into every task.

Tangle `THO-014`, `THO-015`, and `THO-016` demonstrate the desired producer shape: durable reconnaissance routed to the Tangle hub and consumed selectively by later work. The Braintree contract currently defines primary routes, pinned `Depends on`, unresolved `Gated on`, and supersession, but no canonical non-pinned context-reference edge or read expansion for it.

# Outcome

Authors can link optional shared reconnaissance through one canonical relation, and readers can request a bounded orientation packet that includes those references without changing readiness, reachability, or `context_rev` semantics.

# Done when

- The contract defines one canonical relation from a consuming work node to a referenced knowledge node, including allowed target types, direction, multiplicity, and placement.
- The relation is explicitly non-pinned and does not imply readiness, staleness, primary routing, ownership, or automatic context loading.
- `braintree check` validates malformed or invalid uses structurally without claiming semantic authority over whether the context is useful.
- A supported `braintree node` option or equivalent read surface returns the requested node plus its directly referenced reconnaissance in deterministic, bounded output and documents cycle and missing-target behavior.
- Existing node output remains unchanged unless the opt-in expansion is requested.
- Help, authoring or dependency guidance, and tests cover the consumer-authored shape and negative cases.
- `make test` passes.

# Result

The canonical relation is `Informed by [[TARGET]].`, authored in `# Context` on the consumer and stored only there. `TARGET` must be an existing knowledge node (`THO`, `DEF`, or `DEC`); a node may carry several such lines, one per target, and must not repeat a target. The line is non-pinned: it carries no `context_rev`, so it never affects readiness, staleness, primary routing, ownership, or automatic context loading. `braintree.graph_check.REFERENCE_RELATION` and `REFERENCE_LINE` are the one grammar, shared with the read surface through `reference_targets`.

`braintree check` validates structure only, with four stable codes: `reference-malformed` (the line is not exactly the relation shape, for example a pin or missing period), `reference-outside-context`, `reference-target-type`, and `reference-duplicate`. A missing target stays `node-broken-link` rather than a second finding.

`braintree node references NODE` is the opt-in read surface. It resolves the requested node and lists its directly referenced reconnaissance as `id,status,context_rev,summary` rows sorted by target name, so output is deterministic. Expansion is exactly one hop, so a reference cycle between two nodes terminates and output is bounded by the node's direct references; a target absent from the vault is reported with status `missing` rather than dropped or fatal. Plain `braintree node NODE` is byte-identical to before, and the relation is parsed by the derived index but is not a context edge, so `impact` and `stale` are unchanged.

`references/authoring.md` owns the consumer-authored shape and negative cases, `references/dependencies.md` states the relation is neither pin nor gate, `src/braintree/help.py` publishes `node references` help, and `src/braintree/node_references.py` carries the verb because `cli.py` is frozen observable prompt content. `tests/test_graph_check.py` covers every finding and the quoted/prose non-matches, and `tests/test_node_references.py` covers ordering, one-hop cycle termination, missing targets, deduplication, and the unchanged plain `node` output. `make test` passes.
