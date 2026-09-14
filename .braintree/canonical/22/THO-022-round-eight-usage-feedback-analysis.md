---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Round-eight Tangle feedback confirms seven independently resumable Braintree contract changes, one duplicate already owned by round seven, and three project-local findings disposed.
---

# Question

Area [[IDX-001-execution-graph]].

`braintree feedback scan /Users/thomasmarsh/git/tangle` reports four proposed
feedback nodes recorded after the round analyzed in
[[THO-021-round-seven-usage-feedback-analysis]]: Tangle `FBK-026` through Tangle
`FBK-029`, all recorded at `0.6.0+g3bacaf5`. Which findings still hold against
this implementation at that revision, which are duplicates or already admitted,
and what self-improvement work do they require?

# Context

`FBK-026` and `FBK-029` bundle several findings each. `FBK-026` finding 1 and
`FBK-029` finding 5 are the same resolution-ordering friction; `FBK-026` finding
3 and `FBK-029` finding 1 both concern the compile-and-golden closure; `FBK-026`
finding 2 and `FBK-029` finding 2 are the same timeout-recovery friction; and
`FBK-028` finding 3 and `FBK-029` finding 4 are the same matrix-tolerance
friction. Verified with exact `rg` searches of `SKILL.md`, `references/`, and
`src/` at the recorded revision; no scratch-vault state was needed because these
are contract-text questions.

# Conclusion

| Feedback | Verdict | Evidence |
|----------|---------|----------|
| Tangle `FBK-026` finding 1 | duplicate, already admitted | Same outcome as round seven [[TAS-139-resolved-child-completion-path]]: the resolved-child worker completion path and the multi-writer transient. The new recurrence is cited there; no new node. |
| Tangle `FBK-026` finding 2 | open, admitted | `rg -in 'timed?.?out|re-dispatch|revert' references/coordination.md SKILL.md` matches nothing: the reference states the principle of capturing a partial diff but gives no resume/revert/re-dispatch procedure. |
| Tangle `FBK-026` finding 3 | open, admitted | `rg -in 'lockfile|manifest|Cargo.lock' references/coordination.md` matches nothing; the closure enumerates `tests/golden/**` and `baselines/**` only. Merged with `FBK-029` finding 1. |
| Tangle `FBK-026` finding 4 | open residual, admitted | `SKILL.md` states the worker clamp and that a coordinator stamps the real UTC time, but never says the coordinator must stamp the host clock rather than a rounded or estimated value it then carries all session. |
| Tangle `FBK-026` finding 5 | open, admitted | `rg -in 'negative assertion|source-text|falsification probe|absence' SKILL.md references/` matches nothing: no rule for proving the absence of a named-mode branch. |
| Tangle `FBK-027` | open, admitted | `rg -in 'dead.?code|live consumer|warnings-as-errors|just-in-time|independently acceptable' SKILL.md references/` matches nothing: decomposition guidance has no live-consumer rule under warnings-as-errors. |
| Tangle `FBK-028` finding 1 | open, admitted | No match for `enumerat|gates my artifact|test suite` in `SKILL.md` or `references/`; a brief does not require naming the existing suites that enumerate a directory a new artifact enters. |
| Tangle `FBK-028` finding 2 | disposed, project-local | An authored `demand[].spawn.rate.interval_s` window the kernel never reads is a Tangle schema/kernel defect, not a Braintree contract. |
| Tangle `FBK-028` finding 3 | disposed, project-local | A benchmark-matrix tolerance naming a fixture form the authored schema cannot express is Tangle matrix process; same finding as `FBK-029` finding 4. |
| Tangle `FBK-029` finding 1 | open, admitted | `rg -in 'generated|snapshot|pinned-hash|schema' references/coordination.md` matches no closure enumeration; merged with `FBK-026` finding 3. |
| Tangle `FBK-029` finding 2 | duplicate, merged | Same timed-out-worker recovery as `FBK-026` finding 2. |
| Tangle `FBK-029` finding 3 | open, admitted | Neither `SKILL.md` nor `references/authoring.md` says who records the single session `FBK`; the session produced three. |
| Tangle `FBK-029` finding 4 | duplicate, merged | Same as `FBK-028` finding 3. |
| Tangle `FBK-029` finding 5 | duplicate, already admitted | Same as `FBK-026` finding 1; routed to [[TAS-139-resolved-child-completion-path]]. |

Disposed without admission:

- Tangle `FBK-028` finding 2 and finding 3 are Tangle-project defects and
  process; admitting them would create nodes this repository cannot resolve.
- Tangle `FBK-026` finding 1, `FBK-029` finding 2, and `FBK-029` finding 5 are
  merged into admitted outcomes rather than duplicated as their own nodes.

# Decision

Create the coordinating task
[[TAS-153-usage-feedback-hardening-round-eight]] with one child per
independently resumable confirmed change:

- [[TAS-154-coordinator-clock-stamping]] - Tangle `FBK-026` finding 4.
- [[TAS-155-negative-assertion-guidance]] - Tangle `FBK-026` finding 5.
- [[TAS-156-just-in-time-slice-live-consumer]] - Tangle `FBK-027`.
- [[TAS-157-brief-names-entered-gates]] - Tangle `FBK-028` finding 1.
- [[TAS-158-write-set-closure-generators-and-manifests]] - Tangle `FBK-026` finding 3 and `FBK-029` finding 1.
- [[TAS-159-timed-out-worker-recovery]] - Tangle `FBK-026` finding 2 and `FBK-029` finding 2.
- [[TAS-160-single-session-feedback-ownership]] - Tangle `FBK-029` finding 3.

The round is `P2`; all seven confirmed findings are contract-clarity rules rather
than behavior changes, so nothing blocks coordination. Maintainer-directed
interaction-surface work that is not feedback-derived is tracked separately in
[[TAS-161-routine-interaction-zero-ceremony]].
