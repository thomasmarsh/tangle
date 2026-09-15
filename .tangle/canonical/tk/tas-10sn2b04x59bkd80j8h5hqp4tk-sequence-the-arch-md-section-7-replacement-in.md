---
context_rev: 1
status: proposed
updated: 2026-09-15T20:38:27Z
summary: Sequence the ARCH.md section 7 replacement in slices with explicit deletions.
next: "[[tas-6rtfr5av742kr8b2n7jvkxyr1c-separate-research-evidence-from-the-runtime]]"
---

Area [[IDX-001-execution-graph]].

# Context

ARCH.md ("a small core with useful layers") is an architecture proposal, not an
adopted change. Its section 7 sequences a replacement in five slices with
explicit deletions: separate evidence from the runtime; introduce the shared
graph model; replace the daily read path; consolidate authoring and
instructions; then add composed views and opt into concurrency or search only
when needed. This node coordinates that program. It is not a mandate to
reproduce every current command: ARCH.md's simplifying decision is one parser,
one resolver, one editing path, and fewer mandatory operating rules, and feature
parity with every experimental verb is explicitly not a shipping condition.

This is a first, high-level pass. Each direct child names one ARCH.md section 7
slice (or its cross-cutting verification) and states in its own `# Scoping`
section whether it must be decomposed into finer-grained, session-scoped tasks
before dispatch. The existing ASTRA implementation thrust
([[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]])
and the opt-in coordination thrust
([[TAS-192-deliver-opt-in-parallel-graph-mutation-and]] through
[[TAS-204-full-census-indexing-markdown-views]]) are prior commitments that
overlap some slices; the children reference rather than duplicate them.

# Outcome

The ARCH.md section 7 replacement is sequenced, and every slice carries a
scoping verdict so a session either dispatches a bounded unit or expands the
slice before dispatch.

# Done when

- Every direct child has a `# Scoping` verdict and is either decomposed into
  session-scoped tasks or confirmed executable as authored.
- The parent's `next` preserves the section 7 slice order unless dependency
  evidence justifies reordering.
- The direct children are resolved or deliberately disposed, and the result is
  rolled up from their evidence rather than from child counts.
