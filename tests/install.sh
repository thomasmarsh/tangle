#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM

project="$test_root/project"
home_root="$test_root/home"
mkdir -p "$project" "$home_root"

dry_run=$($repo_root/scripts/install.sh --codex --project "$project" --dry-run)
case "$dry_run" in *"$project/.agents/skills/knowledge-execution-graph"*) ;; *) exit 1;; esac
[ ! -e "$project/.agents" ]

$repo_root/scripts/install.sh --codex --project "$project" >/dev/null
cmp -s "$repo_root/SKILL.md" "$project/.agents/skills/knowledge-execution-graph/SKILL.md"
cmp -s "$repo_root/agents/openai.yaml" "$project/.agents/skills/knowledge-execution-graph/agents/openai.yaml"
cmp -s "$repo_root/scripts/graph-check.rb" "$project/.agents/skills/knowledge-execution-graph/scripts/graph-check.rb"
ruby "$project/.agents/skills/knowledge-execution-graph/scripts/graph-check.rb" "$repo_root/nodes" >/dev/null

repeat=$($repo_root/scripts/install.sh --codex --project "$project")
case "$repeat" in *'result: "no-op"'*) ;; *) exit 1;; esac

$repo_root/scripts/install.sh --codex --home "$home_root" >/dev/null
cmp -s "$repo_root/SKILL.md" "$home_root/.agents/skills/knowledge-execution-graph/SKILL.md"

$repo_root/scripts/install.sh --claude --project "$project" >/dev/null
cmp -s "$repo_root/SKILL.md" "$project/.claude/skills/knowledge-execution-graph/SKILL.md"
cmp -s "$repo_root/scripts/graph-check.rb" "$project/.claude/skills/knowledge-execution-graph/scripts/graph-check.rb"

$repo_root/scripts/install.sh --claude --home "$home_root" >/dev/null
cmp -s "$repo_root/SKILL.md" "$home_root/.claude/skills/knowledge-execution-graph/SKILL.md"
[ ! -e "$home_root/.claude/skills/knowledge-execution-graph/agents" ]

claude_project="$test_root/claude-project"
claude_home="$test_root/claude-home"
mkdir -p "$claude_project" "$claude_home"

claude_dry_run=$($repo_root/scripts/install-claude.sh --project "$claude_project" --dry-run)
case "$claude_dry_run" in *'result: "dry-run"'*"$claude_project/.claude/skills/knowledge-execution-graph"*) ;; *) exit 1;; esac
[ ! -e "$claude_project/.claude" ]

$repo_root/scripts/install-claude.sh --project "$claude_project" >/dev/null
cmp -s "$repo_root/SKILL.md" "$claude_project/.claude/skills/knowledge-execution-graph/SKILL.md"
cmp -s "$repo_root/scripts/graph-check.rb" "$claude_project/.claude/skills/knowledge-execution-graph/scripts/graph-check.rb"
[ ! -e "$claude_project/.claude/skills/knowledge-execution-graph/agents" ]
claude_repeat=$($repo_root/scripts/install-claude.sh --project "$claude_project")
case "$claude_repeat" in *'result: "no-op"'*'agent: "claude"'*) ;; *) exit 1;; esac

$repo_root/scripts/install-claude.sh --home "$claude_home" >/dev/null
cmp -s "$repo_root/SKILL.md" "$claude_home/.claude/skills/knowledge-execution-graph/SKILL.md"
cmp -s "$repo_root/scripts/graph-check.rb" "$claude_home/.claude/skills/knowledge-execution-graph/scripts/graph-check.rb"
[ ! -e "$claude_home/.claude/skills/knowledge-execution-graph/agents" ]

if $repo_root/scripts/install.sh --codex >/dev/null 2>&1; then exit 1; fi
if $repo_root/scripts/install.sh --codex --project "$project" --unknown >/dev/null 2>&1; then exit 1; fi
error=$($repo_root/scripts/install.sh --codex 2>/dev/null || true)
case "$error" in *'error: "agent and destination scope are required"'*) ;; *) exit 1;; esac
for installer in "$repo_root/scripts/install.sh" "$repo_root/scripts/install-claude.sh"; do
  for flag in --version -v -V; do
    [ "$("$installer" "$flag")" = 0.3.1 ]
    if "$installer" "$flag" extra >/dev/null 2>&1; then exit 1; fi
    mixed=$("$installer" "$flag" extra 2>/dev/null || true)
    case "$mixed" in *'error: "unknown argument: '*) ;; *) exit 1;; esac
  done
done

help=$($repo_root/scripts/install.sh --help)
for expected in 'options[8]{flag,meaning}:' 'claude_wrapper: "scripts/install-claude.sh omits --claude and accepts the same destination flags."' '"--help, -h"' '"--version"' '"-v, -V"' 'examples[3]{command,purpose}:' '--codex --project /path/to/project --dry-run' '--claude --project /path/to/project' '--codex --home $HOME'; do
  case "$help" in *"$expected"*) ;; *) exit 1;; esac
done

claude_help=$($repo_root/scripts/install-claude.sh --help)
for expected in 'usage: "scripts/install-claude.sh (--project DIR | --home DIR) [--dry-run]"' 'options[6]{flag,meaning}:' 'examples[3]{command,purpose}:' './scripts/install-claude.sh --project /path/to/project --dry-run' './scripts/install-claude.sh --home $HOME'; do
  case "$claude_help" in *"$expected"*) ;; *) exit 1;; esac
done
case "$claude_help" in *'--claude'*|*'--codex'*) exit 1;; esac
if $repo_root/scripts/install-claude.sh --codex --project "$claude_project" >/dev/null 2>&1; then exit 1; fi
claude_error=$($repo_root/scripts/install-claude.sh --unknown 2>/dev/null || true)
case "$claude_error" in *'error: "unknown argument: --unknown"'*'help: "scripts/install-claude.sh --project <directory> [--dry-run]"'*) ;; *) exit 1;; esac
case "$claude_error" in *'--claude'*|*'--codex'*) exit 1;; esac
claude_missing=$($repo_root/scripts/install-claude.sh --project 2>/dev/null || true)
case "$claude_missing" in *'error: "--project requires a directory"'*'help: "scripts/install-claude.sh --project <directory> [--dry-run]"'*) ;; *) exit 1;; esac

printf 'install tests: passed\n'
