# Knowledge Execution Graph

An Agent Skill for running engineering work through a compact Markdown vault: one atomic node per concern, qualified wikilink edges, authoritative status directories, and local dependency-revision checks.

It is compatible with both Codex and Claude Code because both consume the standard `SKILL.md` skill entrypoint. Codex additionally uses the optional `agents/openai.yaml` interface metadata.

## Install

Clone this repository, then select both an agent and an explicit destination. The installer never writes to `$HOME` implicitly.

```sh
# Project-scoped Codex skill
./scripts/install.sh --codex --project /path/to/project

# Project-scoped Claude Code skill
./scripts/install.sh --claude --project /path/to/project

# User-scoped install only when deliberately naming the home root
./scripts/install.sh --claude --home "$HOME"
```

The destination is `<root>/.agents/skills/knowledge-execution-graph` for Codex or `<root>/.claude/skills/knowledge-execution-graph` for Claude Code. Re-running an unchanged install reports a structured `no-op` result and exits successfully. Inspect a planned destination without writes:

```sh
./scripts/install.sh --codex --project /path/to/project --dry-run
```

Restart the relevant coding-agent session after installing so it discovers the skill. The skill’s own `description` controls automatic selection. To guarantee loading, invoke it as `$knowledge-execution-graph` in Codex or `/knowledge-execution-graph` in Claude Code.

## Verify

The offline test uses only temporary directories; it never creates or updates a live user installation.

```sh
make test
```

## Layout

`SKILL.md` is the portable instruction entrypoint. `agents/openai.yaml` is Codex-specific display metadata. `scripts/install.sh` is a POSIX-shell, AXI-oriented installer that returns compact TOON-style fields on stdout, including structured errors. It copies only distributable files, leaving repository graph state and development files behind.

A vault uses this shape:

```text
nodes/
  index-map.md
  proposed/
  active/
  blocked/
  resolved/
```

The status directory and node filename are authoritative. Node frontmatter stores only local revision, update time, a concise summary, and optional priority, next action, or exceptional disposition. Context-bearing links pin the dependency revision they were last reconciled against. `nodes/index-map.md` holds focus and query recipes; it is not a copied node catalog and is not rewritten after every mutation.

The design and its local 100/1,000/10,000-node comparison with conventional plans, a GitHub-Issues-style fixture, and a Jira-style fixture are documented in [BENCHMARK.md](BENCHMARK.md).

The packaged skill follows the portable Agent Skills convention; see the [Agent Skills specification](https://agentskills.io/specification) and [Claude Code skills documentation](https://code.claude.com/docs/en/skills) for host behavior.
