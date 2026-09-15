---
status: resolved
context_rev: 1
priority: P2
updated: 2026-09-14T23:40:13Z
summary: Fix or dispose the round-eight Hekate feedback findings: timeout recovery, closure completeness, host-clock stamping, negative assertions, just-in-time slices, gate enumeration, and feedback ownership.
---

# Context

Parent [[THO-022-round-eight-usage-feedback-analysis]].

Hekate `FBK-026` through `FBK-029` verified in the parent at `0.6.0+g3bacaf5`.
`FBK-026` finding 1 and `FBK-029` finding 5 are the resolution-ordering friction
already owned by round seven [[TAS-139-resolved-child-completion-path]] and are
not re-admitted. `FBK-028` finding 2 and finding 3 are project-local Hekate
defects and are disposed. `FBK-026` finding 3 and `FBK-029` finding 1 are one
closure outcome and are merged; `FBK-029` finding 2 and finding 4 duplicate
findings admitted here.

# Outcome

Every confirmed round-eight finding is fixed or explicitly disposed, with
regression tests wherever behavior changes.

# Done when

- The coordination reference states the timed-out-worker recovery procedure.
- The compile-and-golden closure names workspace manifests, lockfiles, and
  generated artifacts.
- `SKILL.md` states that a coordinator stamps the host clock at handoff.
- The authoring reference states the negative-assertion and falsification-probe
  rule.
- The decomposition guidance states that a just-in-time slice includes or names
  a live consumer under warnings-as-errors.
- A node or increment brief names the existing test suites that enumerate a
  directory the artifact enters.
- The authoring or coordination reference states who owns the single session
  `FBK` node.
- Every child is resolved or disposed with rationale.
- `make test` passes.

# Children

- [[TAS-154-coordinator-clock-stamping]] - Hekate `FBK-026` finding 4.
- [[TAS-155-negative-assertion-guidance]] - Hekate `FBK-026` finding 5.
- [[TAS-156-just-in-time-slice-live-consumer]] - Hekate `FBK-027`.
- [[TAS-157-brief-names-entered-gates]] - Hekate `FBK-028` finding 1.
- [[TAS-158-write-set-closure-generators-and-manifests]] - Hekate `FBK-026` finding 3 and `FBK-029` finding 1.
- [[TAS-159-timed-out-worker-recovery]] - Hekate `FBK-026` finding 2 and `FBK-029` finding 2.
- [[TAS-160-single-session-feedback-ownership]] - Hekate `FBK-029` finding 3.

# Result

All seven children resolved and every `Done when` criterion is met, so the
coordinating task rolls up from integrated child evidence rather than from child
counts:

- Timed-out-worker recovery: [[TAS-159-timed-out-worker-recovery]] added
  `## Timed-out worker recovery` to `references/coordination.md` — inspect the
  partial diff and its touched tests, re-dispatch a narrow finishing brief or
  accept a green slice on the same node, revert and re-scope a non-green one,
  node stays `proposed` until the finishing worker resolves it, and an
  already-resolved-and-split run needs only coordinator verification. This
  closes Hekate `FBK-026` finding 2 and its duplicate Hekate `FBK-029` finding 2.
- Write-set closure: [[TAS-158-write-set-closure-generators-and-manifests]] named
  the workspace manifest and lockfile a dependency needs and the generated
  artifacts a source shape change invalidates (JSON schemas, snapshots,
  pinned-hash fixtures) in the compile-and-golden closure of
  `references/coordination.md`, closing merged Hekate `FBK-026` finding 3 and
  `FBK-029` finding 1.
- Host-clock stamping: [[TAS-154-coordinator-clock-stamping]] repinned `SKILL.md`
  to "A coordinator stamps the host clock at handoff — the real host clock time,
  not a rounded or estimated value".
- Negative assertions: [[TAS-155-negative-assertion-guidance]] added the
  `## Negative assertions` rule to `references/authoring.md`, accepting a
  checked-in source-text guard when paired with a falsification probe and
  requiring it to name the forbidden tokens and covered modules.
- Just-in-time slices: [[TAS-156-just-in-time-slice-live-consumer]] stated in the
  core's node-boundary guidance that a slice landing a type or trait before its
  consumer is not independently acceptable under warnings-as-errors unless it
  includes a live consumer or its `next` names that consumer as a mandatory
  companion.
- Entered-directory gates: [[TAS-157-brief-names-entered-gates]] requires a
  brief that places an artifact in an existing directory to carry a "gates my
  artifact enters" line naming the enumerating suites before the path is chosen.
- Session feedback ownership: [[TAS-160-single-session-feedback-ownership]]
  states in `references/authoring.md` that the coordinator owns the one session
  `FBK` node and that a worker reports friction in its run report instead of
  creating a node unless the coordinator explicitly grants it.

Every criterion is pinned by a contract test in `tests/test_skill.py`; the
behavioral fixes were made wherever behavior changed, and each slice that added a
contract literal carries a source-named test plus, where the repo convention
applies, a falsification probe that the same guard must reject. Dispositions
rather than admissions: Hekate `FBK-026` finding 1 and `FBK-029` finding 5 remain
owned by round seven [[TAS-139-resolved-child-completion-path]], and Hekate
`FBK-028` finding 2, `FBK-028` finding 3, and `FBK-029` finding 4 are
project-local Hekate defects recorded in
[[THO-022-round-eight-usage-feedback-analysis]] and admitted nowhere here.

Evidence at roll-up: `braintree check` -> `graph check: passed (196 nodes)`;
`make test` -> 655 passed, 3 skipped, 79 deselected. No child pinned a
context-bearing dependency to this node and no node pins it, so `context_rev`
stays at `1`.
