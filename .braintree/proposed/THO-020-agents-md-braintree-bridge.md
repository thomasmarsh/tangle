---
context_rev: 1
priority: P2
updated: 2026-09-13T14:59:19Z
summary: How should durable vault decisions flow into AGENTS.md, and can AGENTS.md shrink to route into Braintree instead of restating contracts?
---

# Question

Area [[IDX-001-execution-graph]].

How should durable decisions and findings flow from the Braintree vault into a
consuming project's `AGENTS.md` as an always-loaded hard store, and conversely,
can `AGENTS.md` be condensed to route into Braintree nodes and references as
needed, without duplicating authority or letting the two drift?

# Context

`AGENTS.md` is loaded in every session and is the natural hard store for rules an
agent must obey unconditionally. The vault is the durable, human-visible
authority for work state and decisions. Today the two meet only at a thin seam:
`AGENTS.md` mandates using the skill, project conventions, and the
`braintree check` / `make test` gates, while the reasoning behind a rule usually
lives only in a `DEC`/`DEF`/`THO` node. Round-three feedback already showed the
split: Tangle's `AGENTS.md` had to mandate the conventional-commit convention
separately, and [[TAS-064-mechanical-change-commit-path]] had to restate the same
contract in both `SKILL.md` and `AGENTS.md`.

Two directions are proposed:

- Promote: when a decision or finding must bind every future session, confirm it
  into `AGENTS.md` as a terse hard rule, with the vault node as the rationale it
  points to.
- Condense: shrink `AGENTS.md` to pointers and invariants, moving restated
  contract detail back to the vault and the skill references it already loads.

The hazard is duplication: two authorities for one rule drift, and a condensing
pass can drop a rule that was load-bearing. Any design must name which store owns
which fact and how a consumer detects a mismatch.

# Hypothesis

Keep one authority per fact: the vault owns rationale, evidence, and revision;
`AGENTS.md` owns only the small set of invariants that must hold even when the
skill is not loaded, and states each as a pointer into its vault node rather than
a copy. Promotion is an explicit decision recorded in a node, not a manual
mirror; condensation is a bounded pass that first inventories which `AGENTS.md`
rules no longer have a live vault source.

# Test

- Inventory the current `AGENTS.md` rules and classify each as invariant,
  pointer, or duplicated contract.
- Decide the promotion trigger and the node that authorizes it, and how a
  `DEC`/`DEF` records that it was promoted.
- Decide how condensation preserves load-bearing rules and whether a test or
  check can detect `AGENTS.md`/vault divergence.
- If adopted, state the contract text and the installer/`AGENTS.md` changes; if
  rejected, record why here.
