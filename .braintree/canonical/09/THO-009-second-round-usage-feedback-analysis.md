---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Round-two Hekate feedback: six findings reproduce at 0.4.0 across the stale-pin commit shape, claim hashes, a silent release, dependency status, and mechanical commits.
---

# Question

Area [[IDX-001-execution-graph]].

The Hekate vault recorded four Braintree friction nodes after the round analyzed
in [[THO-008-external-usage-feedback-analysis]], the Hekate nodes
`THO-004-terminal-survey-braintree-friction`,
`THO-005-braintree-friction-kitty-spike`,
`THO-006-braintree-friction-shared-render-layer`, and
`THO-007-braintree-friction-tui-session`. Their ids collide numerically with
this vault's own `THO-004`-`THO-007`, so they are cited as `Hekate THO-00N`.
Which findings still hold against
this implementation at `0.4.0` (`e77839c`), and what self-improvement work do
they require?

# Conclusion

All six round-two findings reproduce; none was fixed by
[[TAS-044-usage-feedback-hardening]] or later work. Reproduction used an
isolated sidecar via `BT_SIDECAR_DIR`/`BT_PROJECT_ID` and a throwaway vault in
`/tmp`, so no real reservation state was disturbed. The Hekate source nodes are
`THO`, not `FBK`, so they carry no `braintree_revision` frontmatter; round one
pinned `1dc6fe6`, and this round was verified at `0.4.0` (`e77839c`).

| # | Finding | Source | Kind | Severity | Evidence |
|---|---------|--------|------|----------|----------|
| R1 | A `context_rev` bump leaves pinned consumers stale, so the documented "leave the pin, reconcile later" workflow cannot pass the mandated `graph-check nodes` gate; only `--allow-stale` clears it, and neither `SKILL.md` nor `AGENTS.md` sanctions that | Hekate THO-004 F1 | docs/contract | high | `graph_check.py` rejects a mismatch unless `--allow-stale`; `rg` finds no `allow-stale`, same-commit, or commit-shape statement in `SKILL.md` or `AGENTS.md` |
| R2 | Resolving a frontier knowledge node has no stated effect on the coordinating parent's `next` | Hekate THO-004 F2 | docs | low | `SKILL.md` read/execute and mutation sections never mention `THO`/`DEF`/`DEC` frontier advance |
| R3 | The `bt claim` base hash has no documented algorithm and no command exposes it | Hekate THO-005 F1 | docs/tooling | medium | `_COMMANDS` has no `hash` command; the sidecar stores `sha256(raw file bytes)` with no read path |
| R4 | `bt release` with a mismatched base hash prints `result: "no-op"`, exits 0, and leaves the lease held | Hekate THO-005 F2 | tooling | high | Repro: claim, edit, release with the current hash -> `no-op`, exit 0, `active_claims: "1"`; release with the starting hash -> `released` |
| R5 | A pinned dependency that is still `proposed` passes both `graph-check` and `bt stale` | Hekate THO-006 F1 | checker/docs | medium | `graph-check` passed (3 nodes) with a task pinning a proposed `DEF`; `bt stale` printed `stale: 0 stale dependency pins` |
| R6 | There is no sanctioned commit path for a mechanical change that needs a commit but no independent outcome | Hekate THO-007 F1 | docs/contract | medium | The admission rule rejects mechanical cleanup while `AGENTS.md` rejects an untracked commit |

R1 and R4 are the high-severity findings. R3 and R5 mislead a worker; R2 and R6
are contract gaps.

The documented collection path is not how this vault records feedback:
`feedback-scan ../hekate` prints `feedback: 0 nodes` because Hekate routes
friction through its `IDX-002-braintree-feedback` hub as `THO` nodes and
predates the `FBK` contract. This is disposed rather than admitted: the `FBK`
marker is the deliberate discovery contract, and the hub route was found by
reading `index-map.md`, so no skill change follows from the vault's choice.

# Decision

Create the coordinating task [[TAS-058-usage-feedback-hardening-round-two]] with
one child per independently resumable confirmed change:

- [[TAS-059-stale-pin-commit-shape]] — R1.
- [[TAS-060-knowledge-node-frontier-advance]] — R2.
- [[TAS-061-claim-hash-exposure]] — R3.
- [[TAS-062-release-mismatch-signal]] — R4.
- [[TAS-063-pinned-dependency-status-check]] — R5.
- [[TAS-064-mechanical-change-commit-path]] — R6.
