---
context_rev: 1
priority: P1
updated: 2026-09-12T16:48:09Z
summary: The frontier answers are a candidate list a worker resolves through the coordinator's `next` route, and a plan-text gate no node owns is `blocked`.
---

# Context

Parent [[TAS-081-usage-feedback-hardening-round-three]].

N2: `braintree frontier`, `braintree next --rank`, and `braintree orient`
report every unfinished node whose `next` is an action. For a user-requested
plan whose children are created up front as `proposed`, the coordinator's
sequenced-but-not-frontier siblings therefore appear as equal candidates even
though the contract calls them "not yet at the frontier". N3: the contract also
does not state which status a gate on un-tracked plan text takes.

# Outcome

The frontier answers and the contract agree on the one deliberate frontier
child, and a plan-text gate has a stated status.

# Done when

- `braintree frontier`, `next`, and `orient` either return the coordinator's `next` target as the frontier or the contract states the answer is a candidate list that a worker must resolve through the coordinator.
- The `blocked` versus `proposed` guidance covers a gate on prerequisite plan text that no node owns.
- A vault fixture with an up-front plan and sequenced siblings has regression tests for the chosen behavior.
- `make test` passes.

# Result

Took the candidate-list branch the node allows, because the verbs and the
frontier definition are both defensible and only their relationship was
unstated; documenting that relationship needs no new derivation, while
narrowing the verbs to the frontier chain would re-decide how a root task, a
blocked coordinator, and a hub member each reach the frontier.

N2 — `SKILL.md` now states the relationship in both places that describe the
frontier:

- The reachability contract names all three answers (`braintree frontier`,
  `braintree next --rank`, and `braintree orient`) as returning frontier
  candidates: every unfinished node whose `next` is an action, which is a
  superset of the frontier. An up-front plan's sequenced sibling carries its
  own action `next` and is reported beside the deliberate child.
- The read-and-execute loop states the answer is a candidate list, not the
  resolved frontier, and requires resolving it through the coordinator: keep
  only the candidate the coordinating parent's `next` route names; a candidate
  whose parent's `next` names a different node is not yet at the frontier.
- The verb's own help line says it lists frontier candidates.

N3 — `SKILL.md` states that a gate on prerequisite plan text that no node owns
is `blocked`, like any other input the vault does not own, with the prerequisite
and unblock condition in `# Blocked`; once a node owns that plan text the gate
is a sibling dependency and the node is `proposed`. The mutation rule's
`blocked` bullet names the same plan-text case.

Evidence:

- `test_skill_frontier_candidate_contract` and `test_skill_plan_text_gate_status`
  pin the new contract text.
- `_seed_upfront_plan` seeds a proposed coordinator whose `next` names
  `TAS-101-first-step` beside the sequenced `TAS-102` and `TAS-103` siblings:
  `test_frontier_reports_sequenced_siblings_as_candidates`,
  `test_frontier_candidates_resolve_through_the_coordinator`, and
  `test_next_and_orient_report_the_same_frontier_candidates` cover candidate
  reporting and the unique coordinator resolution.
- `make test` and `braintree check nodes` pass.
