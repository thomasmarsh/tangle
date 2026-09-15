---
context_rev: 1
status: resolved
updated: 2026-09-15T14:36:52Z
summary: ASTRA.md architecture-review recommendations vs. current HEAD
---

Area [[IDX-001-execution-graph]].

# Question

ASTRA.md (a requested external architecture review, informed by SKILL.md, the
references, packet/manifest implementation, installer, and test configuration)
proposes nine consolidation thrusts and a suggested execution order. Which of
its recommendations are already resolved by nodes already in this graph, and
which describe real gaps against current HEAD?

# Context

Reviewed against live HEAD rather than the document's own snapshot: read
`src/tangle/packet.py`, ran `tangle packet`, read `src/tangle/main.py`,
`tangle node --help`, `tangle --help`, and `wc -c -w SKILL.md`, and searched
the vault for prior coverage of each thrust.

# Conclusion

| ASTRA thrust | Verdict | Evidence |
|---|---|---|
| §1 progressive disclosure, one skill not many | resolved | [[DEC-004-compact-skill-text]], [[THO-016-has-cumulative-contract-growth-invalidated-the-c]], [[TAS-105-refactor-braintree-into-a-concise-core-skill-wit]] moved conditional detail into `references/*.md`. |
| §1 further shrink toward ~400-700 words | open, folded in | `wc -c -w SKILL.md` still reports 2,292 words / 15,511 B, matching ASTRA's own count exactly. No further compaction has been evaluated since [[TAS-105-refactor-braintree-into-a-concise-core-skill-wit]] landed. |
| §2 finish the execution packet | confirmed gap | Live `tangle packet` on `TAS-204` prints `files[1]{path}: "canonical/04/TAS-204-..."` -- literally only the task's own path. `src/tangle/packet.py` never imports `manifest.py`; no manifest assembly, no acceptance context, and no scoped node/initiative input exist. |
| §3 composed human initiative document | confirmed gap | `views.py` (landed by [[TAS-204-full-census-indexing-markdown-views]]) generates by-status, by-area, by-priority, recent, and external-project pages, but nothing answers goal/approach/decisions/remaining-work for one initiative. |
| §4 admission shortcut refinement | confirmed gap | SKILL.md's admission section still reads "work planned to be committed and finished within one session needs no node," the exact session-duration shortcut ASTRA argues conflates duration with durable value. |
| §5 separate workflow state from coordination | in progress, not a new gap | [[TAS-192-deliver-opt-in-parallel-graph-mutation-and]] / [[TAS-193-same-directory-graph-contribution-intake]] / [[TAS-195-immutable-local-change-submission]] through TAS-202 are the current active frontier (`tangle packet` names [[TAS-204-full-census-indexing-markdown-views]] under this chain) and already scope coordination as opt-in machinery layered over a single-worker default. |
| §6 repo-local vault, central catalog later | not near term | Already the shipped model ([[DEC-002-hybrid-markdown-sqlite-authority]], [[DEC-008-vault-lives-under-dot-braintree]]); ASTRA itself defers a central catalog until a team needs independently versioned planning. |
| §7 identity ergonomics (short/mnemonic id handles) | confirmed gap | `tangle node --help` accepts only "bare ID or full node name"; no short-prefix or alias resolution exists for the 26-character Crockford ids new writes generate. NOTES.md independently flags this friction. |
| §7 installation diagnostic and duplicate-skill repair | confirmed gap | No `tangle`-command diagnostic surface reports discovered skill/program copies per agent and scope; the reported duplicate `pi` install remains undiagnosed, as ASTRA states. |
| §7 uv cache / installed launcher friction | resolved | [[TAS-166-installed-launcher-without-a-uv-cache]] and [[TAS-164-interactive-install-target-selector]]. |
| §8 isolate dev/benchmark dispatch from ordinary commands | confirmed gap | `src/tangle/main.py` imports `behavioral_benchmark`, `memory_authority`, `memory_causal`, `memory_corpus`, `memory_diagnostics`, `memory_pilot`, `token_benchmark`, `verb_benchmark`, etc. unconditionally alongside ordinary command dispatch. |
| §8 frozen-file-avoidance seam | already established pattern | `census.py` and `allocate.py` already live beside `index.py` rather than editing frozen `cli.py`, the exact seam ASTRA asks for; [[TAS-042-retarget-installers-tests-docs-and-remove-ruby]] removed Ruby from that boundary. |
| §9 cheap offline evaluation before live-agent spend | methodology, not a node | Applies as an evaluation constraint on other work rather than a standalone outcome; folded into the packet child's acceptance criteria. |

# Decision

Create [[tas-6xbmmh3mjj7mzn98dctj1745nh-astra-md-feedback-decide-and-implement-the]] with six independently durable children covering the confirmed gaps (§2, §3, §4, and two §7 items, and §8), explicitly not duplicating the in-progress §5-6 coordination thrust and not admitting the §1, §6, §7-cache, §8-seam, or §9 rows, which are already resolved, already the shipped model, or methodology rather than a node.
