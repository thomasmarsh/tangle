# Design Questions and Exploration

> [!NOTE]
> This is one of the few files in this repo that is human
> maintained. AGENTS: do not modify this file.

Tangle is an experiment in managing the complexity of managing
evolving work of multiple agents. There are numerous solutions
to this, including Kanban boards, GitHub Actions MCP, big
directories of plan files, etc.

This project takes a middle ground between human navigable
markdown files and structured interactions with the graph of
knowledge they represent.

It is largely developed organically as a first pass. The project
is promising, but suffers some challenges. But it has provided
a lot of empirical feedback.

## What I like

- The vault is largely navigable by Obsidian graph and makes sense

- Work truly is a rich graph which is not well represented by
  epic/story/task/wave/etc. breakdowns. This is captured.

- It is convenient to have simple mechanisms to say "what's next?"
  and get an authoritative and defensible answer.

- The structured parts of the system are mechanically verifiable
  and enforced; providing tangible benefits.

## Challenges

- Fragmentation of nodes helps minimize token burden, but also
  hurts human navigability. Humans aren't as good at loading
  five nodes and establishing context like agents can.

- Agents spend too much time orienting and token spend on
  learning how to leverage a skill can outweight the benefits the
  skill ostensibly provides.

- The knowledge graph works well for a single agent at a time;
  there are some open questions about handling various
  workflows that involve multiple agents. Agents may work on
  separate branches and be merging/rebasing, or worktrees, or
  even working in parallel within the same directory on the same
  branch. Reconciliation may occur frequently or infrequently.

- Maintaining the vault within a project as git tracked resource
  vs. maintaining it in some central location raises differing
  dynamics.

- Agents have trouble separating planning from effort. Sometimes
  tasks are oversized (long sessions) or undersized (fixed
  orientation costs dominate for a trivial change).

- An orchestrator/planner role in an agentic workflow can
  be used to isolate `tangle` usage from other agents, but that
  introduces strong assumptions about workflow.

- Agents have biases with respect to the amount of work
  logging they will proactively perform. It is difficult to
  anticipate when they will and won't be able to follow the
  SKILL well.

- The cost of orientation is a major concern. In a plan file, the
  agents will sometimes lay out relevant paths and even line numbers
  for changes, for example. Although these can drift, they often
  limit agent orienteering waste.

- Establishing benchmarks is difficult, and testing them costs real
  LLM agent time - an expense I'm not ready to pay.

## Intuitions

- The SKILL should likely be extremely short with mostly
  happy path instructions (how to get the next task) and links
  for specific tasks (how to add a new task) so you pay for only
  what you use.

- Vault nodes should be small enough that they can be read in
  full rather than risk context being missed (as happens with large
  plan files).

- Clustering and semantic queries might be helpful in managing the
  vault.

- The vault would benefit from first class hierarchical document
  management from VISION -> PLAN -> task graph.

- Where possible, we should prefer mechanical and transparent
  bookkeeping, indexing, validation, and enforcement. Tangle
  should mostly be a project management oracle and also provide
  obvious and helpful tools for task ingestion.

- Rather than explaining everything to the agent up front, the
  agent should instead receive feedback from the tool as it works.

## Annoyances

- The tests run in parallel but are too expensive and hinder
  iteration speed.

- No thought has been spent on overall architecture. This has grown
  organically. Now that some of the ergonomics have been discovered,
  it is due for a rewrite with a simple core and some extensions.

- The technology choice by the agent was Ruby. I discard this in
  favor of typed Python anticipating clustering work. The current
  implementation is a bit leaky in that agents keep finding they
  need sandboxed uv caches; this is a flaw that should be addressed.

- We transitioned from Jira style task names like TAS-123, which
  are easy to type, to durable hashes with Crockford encoding
  which are not so easy to type or dictate.

- Installation feels hacky at the moment, and I see `pi` is picking
  up two at a time and reporting a conflict.

