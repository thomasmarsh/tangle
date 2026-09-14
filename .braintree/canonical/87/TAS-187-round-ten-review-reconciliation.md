---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Reconcile the two independent round-ten reviews into the delivered contract, checker, and allocation slices.
---

Area [[IDX-001-execution-graph]].

# Context

Two independent reviews covered `72e7968..HEAD` after the round-ten slices
resolved: [[TAS-181-closure-names-resolved-sibling-seams]],
[[TAS-184-brief-names-mixed-capability-case]], [[TAS-182-worker-host-clock-stamp]],
[[TAS-183-localized-red-timeout-repair]], [[TAS-185-check-gate-placement]], and
[[TAS-165-batch-node-allocation]]. Both returned OK with notes: no blocker, one
substantive defect, and a set of contract-clarity, checker-coverage, and
report-only notes.

The substantive defect is in the TAS-183 delivery: the new localized-red bullet's
condition is a subset of the existing "does not compile or fails a touched test"
bullet, so the same state carries two opposite remedies and the blanket revert
the node was admitted to remove is still licensed. The remaining items are a
mis-subjected escalation sentence and its pin, a synthetic falsification probe,
a missing present-`# Context` gate case, a stale gate hint, and report-only
wording.

# Outcome

The round-ten branch integrates with the localized-red branch correctly scoped,
the resolved-sibling escalation sentence well-formed and pinned, the
gate-placement finding covered for a present `# Context`, and every report-only
review note either fixed or disposed with recorded rationale.

# Done when

- `references/coordination.md`'s "does not compile or fails a touched test"
  bullet is scoped to red outside the localized-red conditions, so
  revert-and-re-scope is the fallback only for unknown or non-localized red.
- The resolved-sibling escalation sentence names the worker as its subject and
  `_RESOLVED_SIBLING_CLOSURE_PRECEDENCE_RULE` is re-cut to match it.
- The TAS-181 falsification probe is no longer a synthetic non-verbatim string.
- `tests/test_graph_check.py` exercises a node with a real `# Context` and a
  mis-placed gate, plus a period-less `Gated on` line that stays clean.
- `_gate_hint` names `# Context` as the required location and its pinned
  assertions agree.
- `gate-outside-context` is classified under a gate-placement class in
  `graph_check.py`, not under "Context edges:".
- Report-only notes are recorded as fixed or disposed with rationale in
  `# Result`.
- `make test` passes.

# Findings

- Contract review finding 1 (P1): narrow the revert branch.
- Contract review finding 2 (P2): fix the escalation sentence and re-cut its pin.
- Contract review finding 3 (P2): repair or drop the synthetic probe.
- Contract review finding 4 and code review F1 (P2): present-`# Context` gate
  case and a period-less clean case.
- Code review F2 (P2): `_gate_hint` must name `# Context`.
- Code review F3 (P2): state the `[COUNT]` bound behavior in help.
- Code review F4 (P2): test that `allocate` and `node record` share one counter.
- Contract review findings 5, 6, 7, 8 and code review F5: fix or dispose.

# Result

Resolved.

Substantive defect (contract review finding 1). `references/coordination.md`'s
not-green bullet now reads, verbatim:

> When the partial state does not compile, or fails a touched test outside the
> localized-red conditions above, it is not green: revert it and re-scope the
> remaining slice against the reverted base rather than continuing on a state
> whose behavior is unknown.

The revert branch is therefore the fallback only for unknown or non-localized
red, and no longer overlaps the localized-red bullet's trigger; the
`_TIMED_OUT_WORKER_RECOVERY_RULE` and `_LOCALIZED_RED_RECOVERY_RULE` pins stay
satisfiable because neither pins that clause's opening.

Escalation sentence (contract review finding 2). The parallel-write-set closure
bullet's last sentence now reads, verbatim:

> The worker still stops and escalates when the change alters the seam's
> behavior, its public contract, or the meaning of the landed seam, or when the
> path is owned by another node or a shared hub and neither the compiler nor a
> touched test mechanically forces it.

`tests/test_skill.py` re-cuts `_RESOLVED_SIBLING_CLOSURE_PRECEDENCE_RULE`'s last
substring to that sentence. Replacing the old tail also removed the substring
`stops and escalates for a path owned by another node or a shared hub` from
`_WRITE_SET_CLOSURE_RULE`, so that pin's last substring is re-cut to
`The worker still stops and escalates when the change alters`; without it
`test_write_set_is_the_change_closure` would fail, which is required collateral
of the reword, not a separate change.

Falsification probe (contract review finding 3). `_RESOLVED_SIBLING_CLOSURE_PRE_CHANGE`
is deleted and `test_resolved_sibling_closure_guard_rejects_escalation_only_text`
now probes with the existing `_WRITE_SET_CLOSURE_PRE_CHANGE`, which is verbatim
to the pre-change bullet at `1dab64d` and lacks every precedence substring, so
`pytest.raises(AssertionError)` still holds. No synthetic non-verbatim probe
string remains.

Gate coverage (contract review finding 4, code review F1).
`tests/test_graph_check.py` adds
`test_gate_outside_a_real_context_section_is_flagged`, which seeds a real
`# Context` section and a later `# Outcome` carrying a gate line for
`DEF-001-contract` and asserts exit 1 with the `gate-outside-context` message
`Gated on` `DEF-001-contract` `must appear in # Context`; the previous
outside-context fixtures lacked a `# Context` section, so the mis-placed-gate
branch was uncovered. It also adds
`test_period_less_gate_line_stays_clean`, which asserts exit 0 for a col-0 gate
line naming `DEF-001-contract` with no final period.

Gate hint (code review F2). `_gate_hint`'s clause now reads: a not-yet-resolved
predecessor is recorded in `# Context` as the gate line, so following the
diagnostic cannot itself produce `gate-outside-context`. The two pinned
assertions that quote the hint
(`test_missing_pin_to_unresolved_target_names_the_gated_form` and
`test_pinned_dependency_not_resolved`) are updated to the new wording.

Finding-code class (contract review finding 8). `src/braintree/graph_check.py`'s
module docstring lists `gate-outside-context` under a new
`Gate placement:` class line and drops it from `Context edges:`, matching
`references/dependencies.md`, which records the gate "instead of a context
edge". `FINDING_CODES` insertion order is unchanged.

`[COUNT]` bound (code review F3). `src/braintree/help.py`'s `COUNT` operand says
`positive number of consecutive ids; default 1, no upper bound`, and
`test_allocate_help_and_command_index_name_the_count_operand` pins that wording.
No frozen baseline changed: `benchmark/verb-baseline.json` records stdout for
`frontier`, `node`, `impact`, `orient`, `digest`, and `clusters`, not
`allocate --help`, so no re-freeze was needed.

Shared counter (code review F4). `tests/test_bt_foundation.py` adds
`test_allocate_batch_and_node_record_share_one_counter`: on one project vault and
one sidecar, `allocate TAS 2` returns `TAS-001`/`TAS-002`, and a following
`node record --type TAS` returns `TAS-003`, so the batch allocator and the
capture path provably share one counter.

Dispositions for the report-only findings.

- Contract review findings 5 and 6 are cosmetic wording inside the already
  resolved TAS-182 and TAS-180 `# Result` bodies ("now leads the `updated`
  bullet", "landed in four commits" for five bullets). A resolved node body is
  not in this node's write set and repair would edit resolved evidence, so both
  are recorded report-only, not fixed.
- Review-187 finding 1 (record side effect): resolving this node removed a
  synthetic probe and re-cut `_WRITE_SET_CLOSURE_RULE`'s tail, so
  TAS-181-closure-names-resolved-sibling-seams' `# Result` no longer matched the
  tree. TAS-181 is corrected in place as a factual correction with no
  `context_rev` bump, because no node pins it; its summary and outcome are
  unchanged.
- Contract review finding 7 (`benchmark/memory-corpus/implicit-retrieval.json`
  episode ep-3 paraphrases the pre-TAS-181 escalation clause) is deliberately
  left frozen-historical: it is a recorded decision, not an omission. No test
  fails, because the corpus is content-addressed over its own JSON and the
  manifest hashes no cited file; re-freezing would advance the family digest for
  a paraphrase and change frozen evidence without a behavior change.
- Code review F5 (atomicity pinned only probabilistically) is covered by the
  implementation, not weakened: `allocation.allocate_many` reserves the whole
  batch inside one `sidecar._run_transaction` / `BEGIN IMMEDIATE` with a single
  commit, and the existing concurrency tests in `tests/test_bt_verification.py`
  plus the new shared-counter test pin the outcome. Recorded as covered, not a
  gap needing a new deterministic assertion.

Evidence.

- `uv run pytest tests/test_skill.py tests/test_graph_check.py tests/test_bt_foundation.py -q`:
  243 passed.
- `make test`: 741 passed, 3 skipped, 79 deselected (numpy absent).
- `uv run braintree check`: passed.
- `git status` after the commit: clean.
