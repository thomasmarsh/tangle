---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Round-six Tangle feedback confirms eight independently resumable changes across timestamps, write-set closure, completion receipts, parent-next ownership, status-move staging, resolved-seam reuse, and legacy-vault migration, and disposes the duplicates and already-handled findings.
---

# Question

Area [[IDX-001-execution-graph]].

`braintree feedback scan /Users/thomasmarsh/git/tangle` reports nine proposed
feedback nodes recorded after the round analyzed in
[[THO-014-round-five-usage-feedback-analysis]]: Tangle `FBK-007` through
Tangle `FBK-015`, recorded from `0.5.0+gba362e3` through `0.6.0+g4c6cafb`. The
ids collide with this vault's own `FBK` numbering, so they are cited as Tangle
`FBK-00N`. Which findings still hold against this implementation at `0.6.0`
(`4c6cafb`, re-checked at `c54728a`), which are duplicates or already handled,
and what self-improvement work do they require?

# Conclusion

Reproduction used isolated probes at `/tmp/bt-r6` and `/tmp/bt-ck` with
`BT_NODES_DIR`/`BT_SIDECAR_DIR`/`BT_PROJECT_ID`, so no reservation state and no
vault state was disturbed.

| Feedback | Scan revision | Verdict | Evidence |
|----------|---------------|---------|----------|
| Tangle `FBK-007` | `0.5.0+gba362e3` | open, admitted | `SKILL.md` defines `updated` only as "Refresh `updated` to the current UTC ISO-8601 time on every mutation" and gives no rule for an incoming timestamp ahead of the host clock; `clamp` and `monotonic` match nothing in `SKILL.md` or `references/`. A coordinator's day-boundary placeholder (`updated: 2026-09-13T00:00:00Z` against a `2026-09-12T21:33Z` handoff clock) still forces the worker to choose between two instructions. |
| Tangle `FBK-008` | `0.5.0+gf9b330c` | open, admitted | `references/coordination.md` grants authoring "inside its declared write set" and escalation for "a change that alters a landed seam another node owns", but states no rule for a change whose compile-and-golden closure exceeds the assigned set; `closure` and `compile-and-golden` match nothing. The reported exhaustive `EventRecord` matches in `apps/tangle-cli` and the out-of-crate goldens and `baselines/` remain a coordinator-owned judgment call. |
| Tangle `FBK-009` | `0.5.0+g974b178` | duplicate, merged into `FBK-008` | The node itself says it is "additional evidence for FBK-008": a required golden regeneration outside the write set is the same write-set-closure outcome and needs no separate acceptance. |
| Tangle `FBK-010` | `0.5.0+g974b178` | open, admitted | No `SKILL.md` or reference text names a completion receipt or the `release` result as the completion signal; `receipt` matches only benchmark code. A run reported failed on a report-time timeout while the slice was already committed, node-updated, gated, and released, so the failed status still implies unfinished work. |
| Tangle `FBK-011` | `0.5.0+g974b178` | open, admitted | `SKILL.md` says "the resolving worker owns that edit" with no rule for a write set that excludes the parent. Probe `/tmp/bt-ck`: a valid 3-node vault with an unfinished coordinating parent whose `next: "[[TAS-002-child]]"` names a resolved child passes `braintree check` (`graph check: passed (3 nodes)`), so the stale route is neither assigned nor flagged. |
| Tangle `FBK-012` | `0.5.0+g7b95875` | open, admitted | Neither `SKILL.md` nor `references/` mentions `git mv`, `git add`, or staging; the status rule says only "Change status by moving the unchanged filename between those directories". The `git mv`-stages-the-pre-edit-blob trap (`git show HEAD:nodes/resolved/TAS-037-*.md \| grep -c '^# Resolution'` printed `0` while the worktree printed `1`) is still undocumented. |
| Tangle `FBK-013` | `0.5.0+g7b95875` | duplicate, merged into `FBK-012` | The node itself says "This is FBK-012's finding", the same `git mv` trap across a two-commit claim/resolution split; one staging rule covers both. |
| Tangle `FBK-014` | `0.5.0+g7b95875` | open, admitted | `references/coordination.md` says a change that "alters a landed seam another node owns ... is escalated rather than authored" and states no bookkeeping for an additive optional field the consuming node's own Done-when mandates on a resolved sibling's seam; `additive` matches nothing. |
| Tangle `FBK-015` finding 1 | `0.6.0+g4c6cafb` | open, admitted | `references/coordination.md` has no rule for reusing a resolved sibling's seam by widening visibility instead of duplicating it; `pub(crate)`, `visibility`, and `reuse` match nothing in `SKILL.md` or `references/`, so the internal, non-behavioral path stays a judgment call. |
| Tangle `FBK-015` finding 2 | `0.6.0+g4c6cafb` | partially disposed; announced-migration residual admitted | Probe `/tmp/bt-r6` at `c54728a`: from a root with a legacy `nodes/index-map.md`, `braintree feedback record --route 'Area [[IDX-002-feedback]]' ...` renamed `nodes/` to `.braintree/`, printed `path: "/private/tmp/bt-r6/.braintree/proposed/FBK-001-relocation-probe.md"`, and printed no notice of the move; a following `braintree migrate` was a `no-op`. The relocation is now the decided behavior ([[DEC-008-vault-lives-under-dot-braintree]], [[TAS-109-move-vault-to-dot-braintree]], `66556fa`), so "never relocate implicitly / refuse to write" is disposed; the demonstrated silence, with no notice naming both paths, is not. |

Disposed without re-admission:

- Tangle `FBK-001` through `FBK-006` are fixed or admitted under
  [[TAS-095-usage-feedback-hardening-round-four]] and
  [[TAS-099-usage-feedback-hardening-round-five]]; re-admitting them would be
  node churn.
- Tangle `FBK-009` is folded into the `FBK-008` child; Tangle `FBK-013` is
  folded into the `FBK-012` child. The `git mv` "Recurrence note" in `FBK-015`
  is the same finding and needs no node of its own.
- Tangle `FBK-015` finding 2's prohibition on implicit migration is disposed by
  [[DEC-008-vault-lives-under-dot-braintree]] and
  [[TAS-109-move-vault-to-dot-braintree]]; only the silent-migration residual is
  admitted.
- Tangle `FBK-007`'s secondary note — an integration test needs the tested crate
  surface genuinely public — is a write-set closure member and is subsumed by
  the `FBK-008` child rather than a separate node.

# Decision

Create the coordinating task [[TAS-111-usage-feedback-hardening-round-six]]
with one child per independently resumable confirmed change:

- [[TAS-112-timestamp-clamp-rule]] — Tangle `FBK-007`.
- [[TAS-113-write-set-change-closure]] — Tangle `FBK-008` and the merged `FBK-009`.
- [[TAS-114-completion-receipt]] — Tangle `FBK-010`.
- [[TAS-115-parent-next-advance-ownership]] — Tangle `FBK-011`.
- [[TAS-116-status-move-staging]] — Tangle `FBK-012` and the merged `FBK-013`.
- [[TAS-117-authorized-additive-seam-change]] — Tangle `FBK-014`.
- [[TAS-118-resolved-seam-internal-reuse]] — Tangle `FBK-015` finding 1.
- [[TAS-119-announce-vault-migration]] — Tangle `FBK-015` finding 2.

Round six is `P2`. The findings are contract-clarity and staging hazards a
worker can work around once noticed: most are prose rules, and the one behavior
change (announcing a legacy-vault migration) is a visibility improvement, not
data loss, because the migration is the decided behavior and the Markdown bytes
are unchanged. No finding blocks coordination or makes a command answer wrong,
so the round does not displace the `P1` frontier routed by
[[TAS-087-off-the-shelf-embedding-and-clustering]].
