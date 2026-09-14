---
status: blocked
context_rev: 1
updated: 2026-09-14T23:40:13Z
summary: Demonstrate incremental reviewed intake on representative large plans.
next: Choose pilot plans, permissions, and success thresholds.
---

Parent [[TAS-167-legacy-plan-intake-lifecycle]].

# Context

Gated on [[TAS-170-define-plan-bridge-contract]].

The pilot must exercise the manual protocol before any importer hard-codes its semantics.

# Outcome

Representative plans demonstrate whether a bridge plus just-in-time extraction improves execution resumption without creating a second maintenance burden.

# Done when

For each selected pilot:

1. Preserve the original plan and record its source identity.
2. Create the bridge using the defined authority mode.
3. Extract only the current frontier and the decisions or definitions required to execute it.
4. Resume or execute from those nodes without relying on hidden conversational context.
5. Revisit the source after representative edits and apply the reconciliation rules.
6. Continue extraction only when additional branches approach execution.
7. Record contradictions, authority conflicts, rollback behavior, and any content that never needed migration.

The combined evidence reports:

- nodes created relative to source headings and checkboxes;
- existing owners updated and duplicate nodes avoided;
- contradictions and stale completion claims discovered;
- tokens, files, or source sections needed for cold resumption;
- time spent maintaining or reconciling the two surfaces;
- source changes that invalidated graph assumptions;
- narrative, history, and speculation correctly left outside the graph;
- whether the bridge reduced or merely relocated bookkeeping.

# Blocked

Blocked by: project-owner selection of pilot plans, authorization boundaries, and success thresholds.

Questions for the project owner:

1. Which selected plans may be used for the first manual pilots?
2. Must pilots be read-only simulations, or may they create Braintree nodes and annotate or freeze source plans?
3. Should pilots run in this repository, consuming projects, scratch copies, or a combination?
4. What amount of source material, number of active outcomes, or duration is representative?
5. What improvement in cold resumption or maintenance cost would justify productizing the workflow?
6. Which regressions, document changes, or authority conflicts would make the approach unacceptable?

Unblocks when: the owner selects the pilots, authorizes their mutations, and states usable success and failure thresholds.
