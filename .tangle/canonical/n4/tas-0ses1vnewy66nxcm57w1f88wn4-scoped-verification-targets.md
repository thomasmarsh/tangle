---
context_rev: 1
updated: 2026-09-15T02:19:40Z
status: resolved
summary: Add scoped Tangle verification targets.
---

Parent [[TAS-205-improve-braintree-workflow-efficiency]].

# Outcome

Agents can iterate with a documented affected-surface gate while `make test` remains the final repository acceptance gate.

# Done when

- A stable mapping selects lint, type, graph, and focused test checks by named surface.
- The target is faster than the full suite and fails on a deliberate mapped defect.
- Documentation states that it does not replace `make test` before handoff.

# Result

`scripts/verify-surface.sh` holds the one surface map: `storage`, `index`, `check`, `intake`, `cli`, `semantic`, `memory`, and `benchmarks`. Each surface runs lint, type, `tangle check`, and `git diff --check` first, then only the focused offline tests mapped to it; `benchmarks` adds the opt-in marker that `make test-benchmarks` uses. The Makefile exposes `make verify`, which lists every surface with its mapped files, and a `verify-%` pattern target that delegates to the script; an unknown surface exits 2 and prints the valid list. `README.md` names the surfaces and states they are an iteration gate that never replaces the full suite, which runs before handoff. `tests/test_skill.py` pins that documentation against the script's surface list.

Measured on this host: `make verify-check` takes 6.1 s warm and 27 s with a cold type cache, against 110.8 s for `make test`, so the scoped target is roughly 18x faster than the full suite.

Deliberate-defect evidence: dropping the `current_rev != pinned` to `PROBLEM_MISMATCH` return from `context_pin_problem` in `src/tangle/graph_check.py`, the source mapped to the `check` surface, left lint, type, and the live graph check passing while `make verify-check` exited non-zero with four failures in `tests/test_graph_check.py` (`test_context_rev_mismatch`, `test_pending_advance_sanction_relaxes_nothing_else`, `test_toon_format_emits_a_record_per_finding`, `test_every_error_class_emits_a_documented_code[context-rev-mismatch]`). Reverting the file restored a clean 149-test pass, and the defect was never committed.

TAS-205 advances to [[tas-5f7z20r7we8kafq7t0dws2hj2j-slim-skill-hot-path]] because verification cost is the parent outcome's next cost dimension, while the sibling migration-milestone convention answers a decomposition question rather than a workflow-cost one.
