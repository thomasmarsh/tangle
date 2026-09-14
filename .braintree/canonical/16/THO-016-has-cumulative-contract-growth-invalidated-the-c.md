---
status: resolved
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Keep one Braintree skill, restore a concise entrypoint, and progressively disclose conditional contracts through references.
---

Area [[IDX-001-execution-graph]].

# Question

The compact-skill decision adopted a 13,481-byte `SKILL.md` after a measured 23.5% median token reduction. The current file is 28,282 bytes and 4,249 words. Which newer rules still belong in always-loaded prose, which can move behind direct commands or focused references, and what evaluation is needed before retaining the growth?

# Context

Area evidence: [[DEC-004-compact-skill-text]] requires future skill-text edits to preserve compactness and be evaluated with a matched token A/B. [[TAS-080-staged-token-ab]] is blocked on authorization for a separate direct-answer comparison and does not yet decide the cumulative contract-size question.

# Evidence

`git show 97e0848:SKILL.md | wc -c` reports 13,481 bytes; `wc -c SKILL.md` reports 28,282 bytes. `git diff --stat 97e0848..HEAD -- SKILL.md` reports 109 insertions and 26 deletions.

# Conclusion

The cumulative growth has invalidated the compactness outcome, though not the newer rules themselves. Braintree remains one coherent operating model: vault authority, node admission, frontier execution, dependencies, coordination, and feedback share invariants and are often encountered in one work session. Splitting those modes into independently triggered skills would duplicate the shared contract, create overlapping discovery descriptions, and make cross-skill drift a correctness risk.

Keep one `braintree` skill and apply progressive disclosure inside it. The entrypoint should retain only:

- Markdown/sidecar authority and the minimal vault shape.
- The read-and-execute loop, admission threshold, outcome-based node boundary, status meanings, and core mutation invariants.
- A short dependency readiness rule and routing sentences that say exactly when to read each conditional reference.

Move conditional detail into focused references:

- `references/coordination.md` for claims, leases, parallel worktrees, integration, reconciliation, and multi-host limits.
- `references/dependencies.md` for pins, gates, semantic revision bumps, staged staleness, and reversals.
- `references/authoring.md` for node schemas, feedback nodes, capture commands, disposition, and uncommon lifecycle forms.

Command syntax and examples should live primarily in `braintree --help`; `SKILL.md` should name direct answers and their decision boundary rather than repeat option catalogs. Restore the entrypoint toward the previously measured compact range, then compare behavior and tokens rather than enforcing a byte limit.

The current installer is a prerequisite seam: it copies `SKILL.md` and `agents/openai.yaml` but no reference tree, so progressive disclosure cannot ship until every target installs references and detects their changes. Contract validation also needs restructuring: `tests/test_skill.py` pins many prose fragments, while skill quality guidance favors observable behavior and meaningful invariants over exact generated wording. Preserve critical literal grammar only where clients must emit it; test the rest through fixtures, routing, and behavioral outcomes.

Do not create subskills now. Reconsider one only if a future mode has a distinct user trigger, can be correct without loading the core graph protocol, and has enough conditional detail to outweigh another discovery surface. External feedback collection is the closest candidate, but today its schema and admission handoff still depend directly on the core contract.

# Decision

Admit [[TAS-105-refactor-braintree-into-a-concise-core-skill-wit]] as one coherent implementation task covering entrypoint compaction, reference packaging and routing, contract-test restructuring, and measured verification. These are seams of the same concise-skill outcome, not independent nodes merely because they touch different files.
