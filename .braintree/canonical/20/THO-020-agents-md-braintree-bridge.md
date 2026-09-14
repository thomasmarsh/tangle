---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Adopt one authority per fact - AGENTS.md keeps only pre-skill invariants and routes the rest to SKILL.md and README, shrinking it 14%.
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

# Result

**Adopted: one authority per fact, with a named promotion trigger and a bounded
condensation pass.** `AGENTS.md` keeps only the invariants that must hold before
`SKILL.md` loads and routes every other rule to the surface that owns it; the
duplicated Braintree contract was removed here in the same change. `AGENTS.md`
shrank 4168 to 3581 bytes (-587 B, -14.1%; 36 lines removed, 20 added).

**Test 1 - inventory and classification.** Every rule in the pre-change
`AGENTS.md` fell into one of three classes:

| Rule (pre-change location) | Class | Owning surface |
|---|---|---|
| Conventional-commit format, types, scope, mood, body, breaking-change marker, attribution | invariant (repo-owned) | `AGENTS.md` alone; no vault node owns the format |
| Mechanical-change commit path (bullet 8) | shared consequence | `SKILL.md` admission section owns the rule; retained here because the commit section is where a committer reads it and `SKILL.md` is not yet loaded ([[TAS-064-mechanical-change-commit-path]]) |
| "plan, track, and execute work through the skill" | invariant | `AGENTS.md` (the bridge itself) |
| Read `SKILL.md` and follow its contracts | pointer | `SKILL.md` |
| `.braintree/` authority, sidecar derived/disposable, never edited directly | duplicated contract | `SKILL.md` authority paragraph and vault shape; [[DEC-002-hybrid-markdown-sqlite-authority]], [[DEF-002-hybrid-store-contract]] |
| Orient through `index-map.md`, derive the frontier, admission | duplicated contract | `SKILL.md` Reachability, Admission, and Read and execute loop |
| `updated`, `context_rev`, and status-move coherence | duplicated contract | `SKILL.md` frontmatter and Mutation rules |
| `braintree check` / `braintree index` before finishing, and the `--allow-stale` paragraph | duplicated contract (the gate itself is an invariant) | `SKILL.md` Mutation rules; `braintree help dependencies` |
| Installer invocation and interactive-versus-explicit flags | duplicated contract | `README.md` install section |
| `tests/test_skill.py` pins the `SKILL.md` contract strings | invariant | `AGENTS.md`; no other source |
| `make test` / `make test-benchmarks` | invariant | `AGENTS.md`; `SKILL.md` never names the suite |

Classification method: a rule is an *invariant* only when no surface a mandated
read reaches owns it; it is a *duplicated contract* when a live owning surface
exists. Search evidence: `SKILL.md` owns "derived and disposable",
"index-map.md", "frontier", "allow-stale", and "braintree check"; `README.md`
owns the installer invocations; no vault node owns the commit format.

**Test 2 - promotion trigger and the authorizing node.** Promotion is explicit:
a settled `DEC` node whose `# Consequences` names the promoted rule (its text or
a stable anchor) and the commit that landed it. The `DEC` owns the rationale and
evidence; `AGENTS.md` carries the terse rule and points back at the `DEC`. A
promotion is warranted only when a session that has not loaded the skill would
otherwise act wrong or unsafely - the test is "must this bind a session that
never reads the skill?", not "is this rule important?". No new `DEC` was
admitted for this bridge: its conclusion would duplicate this node's outcome
with the same completion evidence and rollback boundary, which the admission
policy rejects as one outcome split across two nodes.

**Test 3 - condensation preservation and divergence detection.** Condensation
may drop a rule only after the inventory shows a live owning surface the
mandatory `SKILL.md` read reaches; a pre-skill invariant survives as a one-line
rule even when its explanation routes (for example "run `braintree check`").
Preservation is now checked:
`tests/test_skill.py::test_agents_md_keeps_the_promoted_invariants` pins the
eight load-bearing strings, so a later condensing pass that drops one fails the
suite and must re-pin deliberately. No check can detect *prose* divergence:
`braintree check` scans only the vault (`graph_check._collect_nodes` globs the
status directories under the nodes dir) and has no knowledge of `AGENTS.md`, and
the only guard over `AGENTS.md` today is
`test_documented_surfaces_hide_the_implementation`, which rejects implementation
leaks. A restatement detector is rejected: matching restated prose either
re-pins `AGENTS.md` text, recreating the duplicated authority it would detect, or
is loose enough to pass while the copies drift. Divergence is prevented by
construction instead - the file states no Braintree contract detail, so the only
cross-store fact is the pointer "read `SKILL.md`", which names no rule that can
drift.

**Test 4 - contract text and the applied changes.** The contract, now in
`AGENTS.md`'s opening paragraph: the file "is the always-loaded hard store. It
carries only the invariants that must hold before `SKILL.md` is loaded, and it
routes every other rule to the surface that already owns it... Promote a vault
decision into this file only through a settled `DEC` node that names the
promoted rule in its consequences." Applied changes: 4168 to 3581 bytes; the
six-item Braintree list collapsed to four (read the skill; run `braintree check`
with the staged-staleness pointer; install via `README.md`; keep
`tests/test_skill.py` strings valid); the `--allow-stale` paragraph and the
installer flags became pointers. Every invariant that tests or agents depend on
survives: the conventional-commit section and the `make test` /
`make test-benchmarks` section are byte-identical, and the surviving rules are
pinned by the new guard. No test pinned the removed prose (`grep` finds only
`test_documented_surfaces_hide_the_implementation` reading `_AGENTS`), and
`test_memory_corpus` uses `AGENTS.md` only as an existing observable path, which
still holds.

Resolving this node leaves the shipped vault with zero unfinished nodes, which
broke `tests/test_bt_index.py::test_frontier_matches_markdown_on_live_vault`:
the live-vault comparison parsed frontier rows and the verb now reports
`frontier: 0 frontier nodes`. Updated deliberately in the same change - the test
still compares the verb against the Markdown recipe, and it now asserts the zero
form when the recipe derives no frontier - rather than seeding a synthetic live
vault, which would have stopped testing the shipped one.

# Decision

Adopt the bridge: the vault owns rationale, evidence, and revision; `SKILL.md`
and its references own the Braintree contract; `README.md` owns distribution;
and `AGENTS.md` owns only pre-skill invariants stated once and routed. Promote
through a settled `DEC`; condense only from the inventory; pin the load-bearing
invariants with a test; detect divergence by construction rather than with a
prose checker. Applied to `AGENTS.md` (-587 B) with the guard added to
`tests/test_skill.py`. No follow-on node is warranted: the decision's only
executable state is the `AGENTS.md` edit and its guard, both landed here, so no
independent outcome remains to resume.
