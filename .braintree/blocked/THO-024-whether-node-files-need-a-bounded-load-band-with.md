---
context_rev: 1
updated: 2026-09-14T00:31:01Z
summary: Whether node files need a bounded load band with split and defragmentation operations.
---

Area [[IDX-001-execution-graph]].

# Question

Should Braintree bound a node's *load size* — the bytes and tokens an agent must
read to consume it — by adopting the two-sided B-tree regime: a target band with
split on overflow and consolidate/flatten on underflow? If so, should the bounds
be enforced, hinted, or only documented?

# Context

The current contract rejects size as a boundary trigger. `SKILL.md` says to
reassess a node boundary "when execution reveals new evidence, not through a
mandatory per-node sizing pass", and to split or consolidate "neither merely
because a session ended, an agent changed, several commits landed, or the work
is larger or smaller than expected". [[THO-019-advisory-size-and-effort-hints]]
resolved that no authored `size:` or capability/effort frontmatter is admitted,
because a coarse token is an unverifiable estimate that re-encodes the boundary
the durable-outcome rule forbids.

This question starts from a different premise. It is not about estimating work
volume; it is about the document as a *load unit*. A node that cannot be read in
one whole-file call wastes context and pushes an agent into partial reads
(`offset`/`limit`), where it can act on a fragment without knowing it. One read
is truncated by the consuming harness at 2000 lines or 50 KB, whichever comes
first, so a larger file is not reliably consumable in one pass at all. A node
should therefore be self-standing and loadable whole, or route detail to linked
documents instead of accumulating it.

Motivating analogy: a bounded-capacity structure (a B-tree) holds occupancy only
when it enforces a floor as well as a ceiling, because splits without merges
drift toward fragmentation. If Braintree adopts only the ceiling, it accumulates
small nodes and rebuilds the traversal cost the ceiling was meant to avoid. The
complete shape is a band: below floor, consolidate or flatten; above ceiling,
split; inside, leave alone.

Why this is not simply a reopening of [[THO-019-advisory-size-and-effort-hints]]:
that node rejected an *authored estimate* used for decomposition and delegation.
This asks about an *observed, verifiable* file property (bytes, lines, headings)
feeding a different consumer decision — can this be read in one pass, or must it
be split or called out. "Self-standing" also has a content test, not only a byte
test: a split must leave each part understandable on its own.

Vault baseline for this repository (199 nodes): largest file 10.5 KB and under
300 lines; 45 nodes exceed 4 KB, 17 exceed 6 KB, and 5 exceed 8 KB. Nothing is
near the 50 KB harness cap, but token waste and partial-read temptation begin
well below it, so the live question is the soft budget, not the cliff.

The analogy is imperfect in ways that raise the cost of the merge half. Unlike
B-tree keys, node IDs are stable and externally referenced by wikilinks,
`context_rev` pins, dependency edges, and Git history, so merging is global and
reference-breaking where splitting is local. The graph is also append-only, so
underflow cannot mean delete; the costly fragmentation is specifically nodes
that are meaningful only as a set — single-child chains, fragmented clusters,
and stub indexes — not every short node. Index nodes are a distinct class:
their occupancy is routed breadth, not bytes, because membership is derived
rather than stored, so their overflow may call for multi-level indexing rather
than a larger file.

# Hypothesis

The current contract is incomplete for the load-unit concern: a ceiling without
a floor fragments the graph. The coherent regime is a two-sided target band with
split on overflow and consolidate/flatten on underflow, applied per node class,
stated as advisory, and measured structurally (bytes, lines, section and heading
counts, routed breadth) rather than as an authored estimate. Whether the public
surface should enforce, hint, or only document the band is open; the
[[THO-019-advisory-size-and-effort-hints]] resolution constrains only the
authored-estimate form.

# Test

- Define the band: which measure or measures, default bounds, per-type
  variation, and how "self-standing" is checked without granting a command
  semantic authority over scope.
- Define underflow and its operations: single-child chain flatten, stub-index
  coalesce, and fragment consolidation; specify how each preserves wikilinks,
  pins, and dispositions, and why merge cannot be automatic.
- Define advisory surfaces and their exit contract: capture
  (`braintree node record`), pre-read (`node`, `orient`, `digest`), validation
  (`check` advisories, never findings), and vault health (`index`, `status`).
- Decide the index-node recursion: does a hub need multi-level indexing at
  breadth, or does derived membership keep hub files small enough that only
  traversal cost grows?
- Benchmark or otherwise gather evidence: measure whether banding changes read
  tokens, partial-read frequency, and task correctness on a growing vault, and
  compare banded against unbanded. Reopen
  [[THO-019-advisory-size-and-effort-hints]] only if the measured property turns
  out to be the authored estimate in disguise or recreates a per-node sizing
  ritual.
- Reconcile the contract text: the `SKILL.md` boundary prose and this band must
  not contradict, and amending either needs a settled `DEC`.

# Blocked

Blocked by: the deeper analysis this question needs — a settled measure and band,
the underflow operations, and benchmark evidence if the trade-off is close —
which no node in this vault owns yet.

Unblocks when: a follow-on analysis or benchmark node in this graph defines the
band, the underflow operations, and the advisory surfaces with evidence, or the
question is disposed. Admitting that node turns this into a `Gated on` question
in `proposed`, per the dependencies reference.
