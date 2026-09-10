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

repeat=$($repo_root/scripts/install.sh --codex --project "$project")
case "$repeat" in *'result: "no-op"'*) ;; *) exit 1;; esac

$repo_root/scripts/install.sh --codex --home "$home_root" >/dev/null
cmp -s "$repo_root/SKILL.md" "$home_root/.agents/skills/knowledge-execution-graph/SKILL.md"

$repo_root/scripts/install.sh --claude --project "$project" >/dev/null
cmp -s "$repo_root/SKILL.md" "$project/.claude/skills/knowledge-execution-graph/SKILL.md"

$repo_root/scripts/install.sh --claude --home "$home_root" >/dev/null
cmp -s "$repo_root/SKILL.md" "$home_root/.claude/skills/knowledge-execution-graph/SKILL.md"
[ ! -e "$home_root/.claude/skills/knowledge-execution-graph/agents" ]

if $repo_root/scripts/install.sh --codex >/dev/null 2>&1; then exit 1; fi
if $repo_root/scripts/install.sh --codex --project "$project" --unknown >/dev/null 2>&1; then exit 1; fi
error=$($repo_root/scripts/install.sh --codex 2>/dev/null || true)
case "$error" in *'error: "agent and destination scope are required"'*) ;; *) exit 1;; esac
for flag in --version -v -V; do
  [ "$($repo_root/scripts/install.sh "$flag")" = 0.2.0 ]
  if $repo_root/scripts/install.sh "$flag" extra >/dev/null 2>&1; then exit 1; fi
  mixed=$($repo_root/scripts/install.sh "$flag" extra 2>/dev/null || true)
  case "$mixed" in *'error: "unknown argument: '*) ;; *) exit 1;; esac
done

help=$($repo_root/scripts/install.sh --help)
for expected in 'options[8]{flag,meaning}:' '"--help, -h"' '"--version"' '"-v, -V"' 'examples[3]{command,purpose}:' '--codex --project /path/to/project --dry-run' '--claude --project /path/to/project' '--codex --home $HOME'; do
  case "$help" in *"$expected"*) ;; *) exit 1;; esac
done

printf 'install tests: passed\n'
