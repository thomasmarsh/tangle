---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: External Tangle usage confirms three bt defects and five contract gaps in allocation, backlinks, pins, and lifecycle guidance.
---

# Question

Area [[IDX-001-execution-graph]].

The Tangle vault recorded Braintree friction in its
`nodes/resolved/IDX-002-braintree-feedback.md` and
`nodes/resolved/THO-003-braintree-usage-postmortem.md` on 2026-09-12. Which
findings hold against this typed Python implementation at `1dc6fe6`, and what
self-improvement work do they require?

# Conclusion

All eight findings reproduce. Three are tooling defects in `bt`; five are gaps
between what `SKILL.md` states and what `graph-check` or the vault actually
enforce. Reproduction used an isolated sidecar via `BT_SIDECAR_DIR` and
`BT_PROJECT_ID`, so no real reservation state was disturbed.

| # | Finding | Kind | Severity | Reproduction |
|---|---------|------|----------|--------------|
| F1 | `bt allocate` ignores Markdown maxima | tooling | high | After `bt init` and `bt reindex nodes`, `bt allocate TAS`, `IDX`, and `THO` each returned `*-001`, colliding with nodes on disk |
| F2 | Reservations are invisible and unreclaimable | tooling | medium | `bt status` reports only `active_claims`; `bt reindex` never touches `id_sequences` |
| F3 | `bt backlinks` takes only the bare ID and fails silently | tooling | medium | `TAS-008-fit-for-purpose-hardening` printed `0 matching edges`, `TAS-008` printed 9, and `TAS-999` also printed a silent 0 |
| F4 | A context pin must end its line, but the error blames the pin | checker/docs | low | `_CONTEXT_PIN.fullmatch` rejects trailing prose and the message does not name it |
| F5 | `next` grammar lives only in the checker | docs | low | The direct-child test is `routes.get(target) == node.name` in `graph_check.py` |
| F6 | `blocked` versus a planned dependency is ambiguous | docs | low | `SKILL.md` does not contrast the two on an unstarted tree |
| F7 | "Decompose just in time" conflicts with a requested plan | docs | low | `SKILL.md` forbids speculative trees without allowing a user-requested one |
| F8 | `bt stale` and the status-directory contract are ambiguous | tooling/docs | low | `stale: 0 dependency pins` reads two ways; nothing creates or validates `blocked/` |

F1 is the only high-severity, independently reproducible defect. F2 and F3
mislead a worker; F4 through F8 are low-cost contract gaps.

# Decision

Create the coordinating task [[TAS-044-usage-feedback-hardening]] with one child
per independently resumable change:

- [[TAS-045-id-reservation-reconciliation]] — F1 and F2.
- [[TAS-046-backlinks-name-resolution]] — F3.
- [[TAS-047-context-pin-line-contract]] — F4.
- [[TAS-048-frontier-lifecycle-guidance]] — F5, F6, and F7.
- [[TAS-049-output-and-directory-clarity]] — F8.

This is a user-requested plan, so the children are created up front as proposed
work and are resolved or disposed as reality arrives rather than as speculative
decomposition.
