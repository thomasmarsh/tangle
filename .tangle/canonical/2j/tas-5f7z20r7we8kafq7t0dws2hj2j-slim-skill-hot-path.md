---
context_rev: 1
status: resolved
updated: 2026-09-15T02:38:46Z
summary: Reduce the mandatory Tangle skill hot path.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

The mandatory workflow instructions contain only universal safety and execution invariants; conditional detail is loaded on demand.

# Done when

- The core preserves admission, routing, dependency, mutation, and final-gate rules.
- Conditional coordination, migration, and authoring detail is routed through help topics.
- Contract tests demonstrate that a fresh worker can execute the normal path from the smaller core.

# Result

Slimmed the unpinned prose in the mandatory hot path and routed the demoted
migration detail to the existing **authoring** topic. No pinned rule left
`SKILL.md`.

## Size

| Surface | Before (`wc -c`) | After (`wc -c`) |
|---|---:|---:|
| `SKILL.md` | 15,867 | 15,195 |
| `references/authoring.md` | 13,547 | 14,006 |
| `AGENTS.md` (unchanged) | 4,430 | 4,430 |

The core lost 672 bytes (-4.2%) and now sits 805 bytes under the 16,000-byte
bound in `tests/test_skill.py::test_core_stays_concise`.

## Demoted to the authoring topic

`tangle help authoring` carries a new `## Vault location and migration` section:

- The vault resolves at `./.tangle` by default; an explicit directory operand or
  `TANGLE_NODES_DIR` overrides it.
- A legacy `nodes/` vault is renamed to `.tangle/` in place by `tangle migrate`
  or by the default resolver, leaving the Markdown bytes unchanged.
- `canonical/<suffix>/` shards by the last two id characters, so a known node is
  located with a filename search.

The core keeps one routing fact (`./.tangle` is the default vault) and names
vault layout or migration as a trigger in its authoring reference entry.
`src/tangle/help.py` already routes `tangle migrate --help` to the authoring
topic, so no new topic, topic list, purpose row, README entry, or route test was
needed.

## Condensed in place, every pinned fragment kept

- Vault shape: deleted the standalone resolver/migration bullet, the
  `sharded by the last two id characters` and `so a status change is an
  in-place content edit` clauses (the in-place rule stays verbatim under Status),
  and the child/parent-of/indexed-by enumeration.
- Frontmatter: dropped the `consumer-context revision, not an edit counter`
  gloss; the operational increment rule, the `updated` refresh, the status-move
  exception, and all three host-clock rules are unchanged.
- Admission: dropped `, not through a mandatory per-node sizing pass`, which the
  slice rule already states.
- Status: dropped the `blocked` example clause and a redundant `still`; dropped
  the session-boundary tail after `...not a split trigger or a sizing ritual`,
  which repeated the admission boundary rule verbatim.
- Mutation rules: dropped `so no committed state leaves the parent routing to a
  resolved child`; the pending-advance and stale-route sentences that follow
  carry that rule.

## Contract test

`tests/test_skill.py::test_fresh_worker_can_execute_the_normal_path_from_the_core`
derives the normal path from the core itself: every `##` rule area (admission,
status, reachability, dependency, mutation) is still present, the topic set the
core routes to via `tangle help TOPIC` equals `_TOPICS`, and every verb the core
names (`check` included, as the final gate) is a known help entry whose `--help`
exits 0 with the bounded `usage`/`exits[3]` shape.

## Evidence

- `make verify-cli` -> passed: ruff clean, mypy clean, `graph check: passed
  (251 nodes)`, whitespace clean, 137 focused tests pass.
- `make test` -> ruff, strict mypy, 849 passed / 3 skipped / 80 deselected
  (baseline 848 passed), both shell suites pass, `git diff --check` clean.
- `./scripts/tangle check` -> `graph check: passed (251 nodes)`.
- `uv run pytest -q tests/test_memory_authority.py` -> 22 passed, so no frozen
  observable file changed.
- `AGENTS.md` and the seven frozen observable files (`src/tangle/cli.py`,
  `sidecar.py`, `quality_benchmark.py`, `staged_benchmark.py`, `toon.py`,
  `vault.py`, `revision.py`) are untouched.

# Limitations

- The DEC-004 two-round token A/B was not run: it needs live model spend, and no
  owner authorized it. The recorded effect is static size (-672 bytes, -4.2%)
  plus the offline suites; the A/B stays available through the staged harness.
- Only unpinned prose was condensed. The rules `tests/test_skill.py` pins
  verbatim still dominate the core, so a further material cut needs an
  owner-level contract change that moves or drops a pinned rule; that decision
  was deliberately left out of this node.
