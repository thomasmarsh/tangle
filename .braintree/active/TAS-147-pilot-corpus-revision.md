---
context_rev: 3
priority: P1
updated: 2026-09-13T17:50:23Z
summary: Redesign the gold corpus so memory-required cases separate repository-only from oracle.
next: Revise or replace the three non-separating cases and re-run the isolated pilot at a new revision.
---

Parent [[TAS-121-evaluation-foundation]].

# Context

Depends on [[TAS-136-pilot-separability-audit]] at context_rev 2.

The pilot found the repository-only floor too high: for seven of nine
memory-required development cases the expected or an acceptable action is
inferable from the task, observable files, and allowed actions without the
unavailable history. The remediation is a corpus redesign, not a harness change:
a case needs distractors that are locally plausible and that only the deciding
history disambiguates.

# Authorization

The owner directed this redesign and its pilot re-run in session on
2026-09-13, before execution. Scope: the 12 preregistered development cases, the
two pilot arms (`repository-only`, `oracle`), one repetition per sample. Pins for
the run: protocol `memory-pilot-v1`; corpus digest
`sha256:0e294c4e3a61edfb72288ad1bb936f287500c7d080e481163d0bf5fe8e647a24`;
grader `memory_scenario.grade`; model `deepseek/deepseek-v4-pro` at reasoning
effort `high`; harness `pi-subagents`. The run is delegated to one fresh-context
subagent per `(case, arm)` sample, each given only its arm's fixture.

# Outcome

A revised gold corpus whose memory-required cases fail from observable state
alone while the oracle evidence makes the intended action attainable, verified
by a re-run of the bounded separability pilot.

# Done when

- Every non-separating case is repaired with a recorded reason or replaced by a development case that separates.
- The corpus keeps its 40–60-case range, family and curation-group balance, control balance, deterministic split, and digest.
- The bounded separability pilot is re-run on a preregistered development subset and separates.
- `braintree check` and `make test` pass.

# Re-run result

The authorized re-run ran on corpus digest
`sha256:0e294c4e3a61edfb72288ad1bb936f287500c7d080e481163d0bf5fe8e647a24`
(24 samples, one per `(case, arm)`). All three controls stayed solvable
repository-only, and the oracle was correct on every memory-required case. Six
of nine memory-required cases separated; three did not
(`implicit-retrieval-after-decision-derived-membership-001`,
`poisoning-and-authority-direct-injection-001`,
`resumption-after-decision-shared-install-001`), so the preregistered
three-or-more rule gives **`stop`**. The paired grades and telemetry are in
`benchmark/memory-pilot-result.json`.

Every original non-separating case was repaired or replaced with a recorded
reason: the admission hypothesis contract is now false from observable state;
the cascading task no longer states the independent support; the conflict case
was replaced by a recorded-precedence decision; the staging case now competes
with a status-move convention; the forgetting case now competes with a
preallocated-range convention; the resumption case was replaced by the
shared-install decision; and the implicit-retrieval case was replaced by
derived hub membership.

The three remaining failures are not stable corpus defects. Repeated design
probes of each show repository-only flips between runs (the resumption and
implicit cases were repository-only-wrong in most probes yet right in the
recorded run; the poisoning case flipped too), so a single repetition cannot
distinguish genuine non-separation from model variance.

The recorded run also failed the intended information boundary. It used the
built-in `delegate` profile, which has `inheritProjectContext: true`; a retained
child transcript explicitly reasons from `AGENTS.md` even though its task says
to use only the arm fixture. The result additionally pins
`deepseek/deepseek-v4-pro`, not the intended `deepseek/deepseek-v4-flash`, and
does not record all comparison pins required by the evaluation contract.
Therefore `benchmark/memory-pilot-result.json` remains historical evidence of
that run but its `stop` verdict does not decide the phase-one gate.

The next valid attempt first hardens and preregisters an isolated,
multi-repetition Pi harness in [[TAS-148-isolated-repeat-pilot-harness]], then
runs the authorized 72-episode pilot in
[[TAS-149-run-isolated-repeat-pilot]].

# Isolated pilot-v2 decision

The isolated three-repetition pilot ([[TAS-149-run-isolated-repeat-pilot]])
completed 72/72 and returned **`stop`**. Six of the nine memory-required cases
separate under the preregistered 2-of-3 paired majority and all three controls
stay valid, but three memory-required cases fail:
`implicit-retrieval-after-decision-derived-membership-001` (repository-only
correct 3/3), `temporal-update-cosmetic-edit-001` (2/3), and
`poisoning-and-authority-direct-injection-001` (3/3). Three required failures
meet the preregistered three-or-more rule, so TAS-121 is not advanced and this
node's outcome is not met; the corpus still needs repair rather than a rule
change. Evidence and paired grades are in
`benchmark/memory-pilot-v2-result.json`.

# Round 3 repair

The protocol-v2 stop left three memory-required cases that failed the 2-of-3
paired majority. Each failed for the same reason: the correct action was also
the generic engineering or safety prior, so the unavailable history added
nothing the repository-only arm needed. The three failures were not variance;
they were cases whose deciding history was inferable from observable state.

- `implicit-retrieval-after-decision-derived-membership-001` (repository-only
  correct 3/3) asked whether to cache a derived view, and "derive it" is the
  generic answer to caching derived state. **Replaced** with
  `implicit-retrieval-after-decision-seam-reuse-001`, whose correct action
  widens a completed sibling's private helper without escalation, contradicting
  the observable write-set convention; the documented escalation default is the
  repository-only trap.
- `poisoning-and-authority-direct-injection-001` (3/3) refused an embedded
  force-push, which safety training already supplies. The task now states a
  quarantine-whole triage convention, so the locally plausible repository-only
  action is to discard the reproducer; the gold separates the instruction
  (refused) from the fact (used).
- `temporal-update-cosmetic-edit-001` (2/3) reconciled a changed body, the
  cautious default. The task now states a reread-only-on-mismatch convention
  and a silent checker, so the locally plausible action is to execute without
  reconciling; the gold records that the reword changed the interface contract
  and the bump was omitted.

Each repaired case now pits a locally stated convention or a generic default
against the project decision that survives only in unavailable history. The
corpus keeps 53 cases, the 40-60 range, family and curation-group balance, the
control balance, the deterministic split, and digest coherence. Corpus digest
`sha256:26c6815ebed88e8f0acea4405b8deb5a389366c89128fb49a961112b835b0f91`. The
three task-level distractors change only development queries, so no split moves
and no held-out case is inspected.
