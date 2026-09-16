---
context_rev: 2
status: proposed
updated: 2026-09-16T00:15:58Z
summary: Compose views and opt into concurrency or search only on demand.
next: "[[tas-5cs9e9hpsq3497vdd7wfwzc2vc-extract-optional-search-and-semantic-code-from]]"
---

Parent [[tas-10sn2b04x59bkd80j8h5hqp4tk-sequence-the-arch-md-section-7-replacement-in]].

# Context

ARCH.md sections 4, 5, and 7.5 add composed human documents, then opt into
concurrency or search only when needed. Generate an initiative document from
authored intent and the graph, and keep generated pages disposable. Remove the
old runtime's orphaned command paths, retire compatibility on its announced
schedule, and refuse to make feature parity with every experimental verb a
shipping condition.

This overlaps prior commitments:
[[tas-2erspexpncav3j3y4fezsjra7z-compose-an-initiative-view-answering-goal]]
already owns the composed initiative page, and
[[TAS-192-deliver-opt-in-parallel-graph-mutation-and]] through
[[TAS-204-full-census-indexing-markdown-views]] own the optional concurrency and
full-census layers; [[DEC-006-semantic-layer-capability-boundary]] bounds the
optional semantic layer. Reference rather than duplicate.

ARCH.md section 6 gives that optional boundary a physical form under
`extras/search/`. The existing graph preserved the capability rule but omitted
the source-package extraction, leaving clustering, provider, reduction, and
semantic implementation intermingled with the core package.

# Outcome

Composed initiative documents exist, orphaned command paths are removed,
compatibility is retired on schedule, and optional concurrency, search, and
semantic layers are physically and behaviorally outside the core runtime and
opted into only when a requirement justifies them.

# Done when

- The composed initiative view answers goal, approach, decisions, completed
  outcomes, open tasks, and next action with links to authoritative nodes.
- The removed command paths are inventoried and either deleted or explicitly
  retained with a reason.
- Compatibility retirement happens on its announced schedule, and no
  experimental verb is required for the simpler product to ship.
- Search and semantic implementation is moved out of `src/tangle/` behind the
  optional capability boundary, the default installation excludes its optional
  dependencies and implementation, and core answers remain identical when it
  is absent.

# Scoping

Decomposed at the independently acceptable package-boundary outcome for optional
search and semantics. The composed view is already owned and near session-ready;
orphaned-command removal and compatibility retirement still need an inventory
before dispatch; optional concurrency stays gated on a stated requirement.
