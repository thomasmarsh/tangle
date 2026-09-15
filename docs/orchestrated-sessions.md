# Orchestrated sessions

When the user asks to run an **orchestrated**, **resumable**, **multi-slice**, or
**subagent-driven** session, the main session acts as supervisor and routes the
work to short-lived children. This file is the protocol. `AGENTS.md` only points
here; the Tangle skill remains the authority for the work ledger, and
`references/coordination.md` owns the claims, leases, write sets, worktree, and
hand-off mechanics this file assumes.

Ceremony scales to risk. A small, obvious, single-writer slice may run as one
implementer → build → review chain with short prose hand-offs. Reserve worktree
isolation, warmup children, and machine-consumed structured output for the work
that actually needs them; do not run the full protocol for every edit.

## Roles

| Role | Agent tier | Context | May write? | Delivers |
|---|---|---|---|---|
| Parent / supervisor | strong default | session | graph only | intent, routing, arbitration, acceptance, ledger |
| Scout | fast/recon | fresh | report only | compressed orientation |
| Implementer | worker | fresh per slice | one writer | one verifiable slice of edits |
| Build/test | delegate | fresh per build | no | build/test result + timings |
| Build warmup | delegate | fresh | no | a warm environment |
| Reviewer | reviewer | fresh | no | verdict + file:line findings |
| Commit | resume implementer | inherited | yes | the slice commit |

The parent keeps user intent, authority, routing, arbitration, and final
acceptance. It does not do routine work; direct parent edits are small,
intentional interventions (ledger edits, one-line corrections) with a brief
reason.

## Hand-off protocol

Every child brief contains: repo + working directory + ref; authority and
edit boundary; the objective as one verifiable change; the relevant
files/contracts/constraints; acceptance and exact validation commands; the
expected output; and stop/ask conditions.

The slice loop is fixed:

1. **Scout** — only when orientation is missing. Read-only; no tests or
   dependency materialization.
2. **Implementer** — edits the slice. It reports files changed and what to
   verify, and does **not** run the suite.
3. **Build/test agent** — runs the exact commands on the working tree and
   returns a short summary: passed or failed, the failing commands/tests, and
   timings. It never edits. The repository acceptance gate is `make test`; a
   designated `make verify-<surface>` may stand in for it only as an iteration
   gate, never as acceptance.
4. **Fix** — on failure, resume the *same* implementer with the build report,
   then dispatch a *fresh* build agent. Repeat until green.
5. **Reviewer** — fresh context; reads the diff and the changed files; returns
   `OK` / `OK with notes` / `BLOCK` with file:line findings.
6. **Commit** — resume the implementer to commit the reviewed tree, using a
   conventional commit that references the Tangle node in the body. Byte-compare
   the staged diff against the reviewed diff before committing.

Rules that make hand-offs consistent:

- **One writer per checkout at a time.** Scouts and reviewers are read-only.
- **The Tangle graph and its derived local store are an exclusive resource.**
  A worker updates only its own node and status; it never hand-edits the derived
  index or the untracked coordination state. Run `tangle check` before every
  graph commit and hand-off, and route all ledger reads through `tangle` rather
  than parallel raw scans that race the index.
- **Reports scale to the work.** A single sequential build or review returns a
  short bounded summary; reserve an `outputSchema` for multi-child fanout, where
  the parent machine-consumes results. Never parse long child prose for control
  flow.
- **The build agent owns builds; the implementer owns edits; the reviewer owns
  the verdict.** Do not blur these.
- Keep long output out of chat: the build agent writes a report file and
  returns a bounded summary plus its path.

## Efficiency

- Fresh implementer per slice; resume the same one for fixes so it keeps the
  slice's orientation instead of re-scouting.
- Fresh build agent per build; it needs no prior context, so give it a fixed
  command list plus the baseline numbers.
- Fresh reviewer per review.
- One orientation pass: do not dispatch duplicate scouts.
- Provision slow shared tooling once in the parent before dispatch — resolve the
  environment, sync any optional extra, and warm model or package caches — so
  parallel children do not race the same download or lock.
- Isolate concurrent writers in their own worktrees and give each an exclusive
  Tangle node and write set; integrate one worktree at a time.
- Prefer `user` CPU over wall time when comparing test cost on a shared host.
- `make test` already runs lint, types, the parallel suite, the worktree screen,
  and whitespace checks concurrently; do not fan out a second copy of it.

### Build-warmup agent

A dedicated warmup child is worth it only when dependency materialization or
environment build dominates wall time **and** its result is reused by later
children, or when the build agent's context or tool budget is tight and warming
would spend it. Otherwise fold the warmup into the build agent: run the cheap
lint or type pass, then the timed suite in the same child. A separate warmup
child earns its round trip mainly when several subsequent children reuse one
warm environment. Keep its brief minimal — resolve the environment, report
versions and errors, nothing else.

## Known pitfalls

- **`git diff` blind spot.** `git diff` omits untracked files, so a reviewer
  that only sees the diff cannot see a new file and may `BLOCK` because the
  commit would omit it. Before review, the build agent must surface untracked
  files (`git add -N .` or an explicit list) in the evidence; a review must not
  `BLOCK` solely because new files are untracked when the commit step will
  stage them. The commit must `git add` new files and preserve their mode
  (`100755` for scripts invoked as `./x.sh`).
- **The Tangle store is shared across worktrees.** The authoritative Markdown
  and the derived local state are visible to every worktree of the repository.
  Concurrent `tangle` commands coordinate through claims and leases, not through
  file locks you manage; an unclaimed edit to a shared parent, hub, or index is
  a lost-update race. Let the coordinator own shared nodes and integrate one
  worktree at a time.
- **Captured output flushes at the end.** A long `bash` command prints nothing
  until it finishes; minutes of silence are normal. Do not interrupt on the
  watchdog alone — inspect the run's transcript and status first.
- **Needs-attention is not a stall.** Periodic attention signals fire during
  long suites and installs; triage by transcript.
- **Wall time is noisy, `user` CPU is stable.** On a shared host wall can vary
  two-fold between identical runs; compare `user` seconds and record the load
  average.
- **Interrupted children.** Interrupting a workflow child leaves the parent
  workflow partial. Revive the child with `resume` and continue outside the
  workflow; do not silently switch execution mode.
- **Stale diffs.** Regenerate the diff artifact after every fix round, and
  commit only the byte-identical reviewed revision.

## Tangle integration

- Decompose before dispatch; one node per durable outcome, executed as slices.
- Working children update only their own node and status. A coordinating
  parent's `next` advance belongs to the resolving worker when its write set
  names the parent (or its `next` line); otherwise it is a declared pending
  advance (`tangle check --allow-pending-advance PARENT`). The parent's
  resolving edit is the coordinator's alone.
- Every implementing commit references its node (`Refs <node>`, `Closes
  <node>`), and `tangle check` runs before every graph commit and hand-off.
- A worktree slice is not a node boundary; a fresh worker may continue the same
  node, keeping its content update and status change coherent.
- The coordinator records one `FBK` node per orchestrated session for friction
  that touches the Tangle workflow.
