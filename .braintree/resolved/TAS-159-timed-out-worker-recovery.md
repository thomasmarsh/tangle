---
context_rev: 1
priority: P2
updated: 2026-09-13T22:14:02Z
summary: Add the timed-out-worker recovery procedure to the coordination reference.
---

# Context

Parent [[TAS-153-usage-feedback-hardening-round-eight]].

Tangle `FBK-026` finding 2 and Tangle `FBK-029` finding 2 at `0.6.0+g3bacaf5`,
recorded in two separate sessions. A worker exceeded the run window after a
compiling, behavior-preserving refactor but before adding tests or resolving the
node; recovery was entirely manual inspect-diff, run the touched tests, then
accept-or-revert. `rg -in 'timed?.?out|re-dispatch|revert'
references/coordination.md SKILL.md` matches nothing: the reference states the
principle of capturing a partial diff but gives no procedure for deciding between
resuming, reverting, and re-dispatching.

# Outcome

`references/coordination.md` has a timed-out-worker recovery subsection: on
timeout, inspect the partial diff and run the touched tests to establish whether
the partial state is behavior-preserving; when it compiles and passes, re-dispatch
a narrow finishing brief for the remaining slice or accept the coherent slice on
the same node instead of reverting; when it does not, revert and re-scope; the
node stays `proposed` until the finishing worker resolves it; and a worker that
timed out after already resolving and splitting needs only coordinator
verification.

# Done when

- The recovery subsection is in `references/coordination.md` and pinned by a
  contract test.
- The subsection covers the green and non-green partial states, the node staying
  `proposed`, and the already-resolved-and-split case.
- `make test` passes.

# Result

`references/coordination.md` gains a `## Timed-out worker recovery` section
between the worker-handoff and integration sections. It states that a timed-out
run "leaves a partial state, not a lost one" and that recovery is a coordinator
decision taken on evidence rather than a rerun: inspect the partial diff and run
the tests the diff touches to "establish whether that partial state is
behavior-preserving", never reverting the diff unread. A green partial — one
that compiles with its touched tests passing — is either finished by a narrow
re-dispatched brief for the remaining slice (its tests, its `# Result` evidence,
and its status move) or accepted as the coherent slice on the same node instead
of reverting it, because reverting compiling, passing work gains nothing; "The
node stays `proposed` until the finishing worker resolves it", which owns the
resolving edit. A non-green partial — not compiling, or failing a touched test —
is reverted and the remaining slice re-scoped against the reverted base. A run
that timed out after resolving its node and splitting the remainder "needs only
coordinator verification": the resolved node, its recorded evidence, and its
advanced `next` route are the finished slice. This closes Tangle `FBK-026`
finding 2 and its duplicate Tangle `FBK-029` finding 2, where recovery was
manual inspect-diff, touched tests, then accept-or-revert with no stated
resume-versus-revert-versus-re-dispatch procedure.

`tests/test_skill.py` pins the procedure with `_TIMED_OUT_WORKER_RECOVERY_RULE`
(the partial-state framing, the inspect-and-run-touched-tests step, the green
re-dispatch-or-accept path, the non-green revert-and-re-scope path, the
`proposed` status through recovery, and coordinator-only verification of an
already-resolved-and-split run), asserted by the source-named
`test_timed_out_worker_recovery_procedure_is_stated`. The falsification probe
`_TIMED_OUT_WORKER_RECOVERY_SIGNAL_ONLY` feeds the completion-receipt paragraph
— which already names a timed-out run and states no recovery procedure —
through the same `_assert_contains` guard and requires `AssertionError` in
`test_timed_out_worker_recovery_guard_rejects_the_timeout_signal_alone`, so the
test fails when the guard stops detecting the procedure rather than passing
vacuously. The widened rule reported all eight clause groups missing against
both the probe and `HEAD:references/coordination.md`, so neither passes.

`SKILL.md` is unchanged: the procedure is conditional coordination detail for a
multi-writer recovery act, and the core already routes that workflow to
`references/coordination.md`, so adding it to the core would only dilate text the
`test_core_stays_concise` bound keeps narrow.

Evidence: `uv run pytest -q tests/test_skill.py` -> 69 passed; `braintree check`
-> `graph check: passed (196 nodes)`; `make test` -> 653 passed, 3 skipped, 79
deselected. No context-bearing dependency is pinned to this node and no node
pins it, so no consumer reconciliation was needed and `context_rev` stays at
`1`. The parent [[TAS-153-usage-feedback-hardening-round-eight]] named this node
in its write set, so its `next` advanced to
[[TAS-160-single-session-feedback-ownership]] in this change.
