#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM

project="$test_root/project"
home_root="$test_root/home"
mkdir -p "$project" "$home_root"

# The installer stamps the declared version with the source revision it copied
# from. The test mirrors the installer's detection so it can assert the record.
expected_version=$(sed -n 's/^version *= *"\([^"]*\)".*/\1/p' "$repo_root/pyproject.toml" | head -n 1)
[ -n "$expected_version" ]
expected_revision=unknown
if command -v git >/dev/null 2>&1; then
  detected=$(git -C "$repo_root" rev-parse --short=7 HEAD 2>/dev/null || true)
  case "$detected" in
    [0-9a-f][0-9a-f]*) expected_revision="g$detected" ;;
  esac
fi
expected_record="$expected_version+$expected_revision"

# Every installed skill is a `uv` project, and every install also generates
# the single `braintree` command. Compare its copied package tree with the
# repository sources, then prove the installed console script and launcher run.
package_files="pyproject.toml uv.lock .python-version README.md"
for file in "$repo_root"/src/braintree/*; do
  [ -f "$file" ] || continue
  package_files="$package_files src/braintree/$(basename -- "$file")"
done

check_tree() {
  destination=$1
  cmp -s "$repo_root/SKILL.md" "$destination/SKILL.md"
  for relative in $package_files; do
    cmp -s "$repo_root/$relative" "$destination/$relative"
  done
}

check_record() {
  destination=$1
  [ "$(cat "$destination/src/braintree/installed-revision")" = "$expected_record" ]
}

mtime() {
  stat -f %m "$1" 2>/dev/null || stat -c %Y "$1"
}

# Every install writes the single `braintree` command to <root>/.local/bin and
# it must expose the same revision as the installed console script.
check_launcher() {
  launcher="$1/.local/bin/braintree"
  [ -x "$launcher" ]
  [ "$("$launcher" --version)" = "$expected_record" ]
}

run_installed() {
  destination=$1
  uv run --project "$destination" --frozen --quiet braintree check "$repo_root/nodes" >/dev/null
  uv run --project "$destination" --frozen --quiet braintree feedback scan "$repo_root/nodes" >/dev/null
  [ "$(uv run --project "$destination" --frozen --quiet braintree --version)" = "$expected_record" ]
  run_installed_feedback_record "$destination"
}

# The recording half of the feedback mechanism must work from an installed
# skill in a consuming project, not only from this source repository.
run_installed_feedback_record() {
  destination=$1
  vault=$(mktemp -d "$test_root/feedback.XXXXXX")
  mkdir -p "$vault/nodes/resolved"
  cat >"$vault/nodes/index-map.md" <<'EOF'
# Root hubs

- Indexes [[IDX-001-root]]
EOF
  cat >"$vault/nodes/resolved/IDX-001-root.md" <<'EOF'
---
context_rev: 1
updated: 2026-09-12T00:00:00Z
summary: Root hub.
---
EOF
  uv run --project "$destination" --frozen --quiet braintree feedback record \
    --nodes "$vault/nodes" \
    --attempted 'Ran the installed command.' \
    --friction 'The installed recording path was untested.' \
    --improvement 'Exercise it in the install test.' >/dev/null
  uv run --project "$destination" --frozen --quiet braintree check "$vault/nodes" >/dev/null
  grep -q "braintree_revision: $expected_record" "$vault"/nodes/proposed/FBK-001-*.md
  rm -rf "$vault"
}

dry_run=$($repo_root/scripts/install.sh --codex --project "$project" --dry-run)
case "$dry_run" in *"$project/.agents/skills/braintree"*) ;; *) exit 1;; esac
[ ! -e "$project/.agents" ]
[ ! -e "$project/.local" ]

$repo_root/scripts/install.sh --codex --project "$project" >/dev/null
codex_destination="$project/.agents/skills/braintree"
check_tree "$codex_destination"
check_record "$codex_destination"
cmp -s "$repo_root/agents/openai.yaml" "$codex_destination/agents/openai.yaml"
run_installed "$codex_destination"
check_launcher "$project"

record_path="$codex_destination/src/braintree/installed-revision"
record_mtime=$(mtime "$record_path")
launcher_path="$project/.local/bin/braintree"
launcher_mtime=$(mtime "$launcher_path")
repeat=$($repo_root/scripts/install.sh --codex --project "$project")
case "$repeat" in *'result: "no-op"'*) ;; *) exit 1;; esac
[ "$(cat "$record_path")" = "$expected_record" ]
[ "$(mtime "$record_path")" = "$record_mtime" ]
[ "$(mtime "$launcher_path")" = "$launcher_mtime" ]

# A changed installed revision is detected and restamped, not reported no-op.
printf '%s\n' '0.0.0+gold' >"$record_path"
upgrade=$($repo_root/scripts/install.sh --codex --project "$project")
case "$upgrade" in *'result: "installed"'*) ;; *) exit 1;; esac
check_record "$codex_destination"

$repo_root/scripts/install.sh --codex --home "$home_root" >/dev/null
cmp -s "$repo_root/SKILL.md" "$home_root/.agents/skills/braintree/SKILL.md"
check_launcher "$home_root"

pi_dry_run=$($repo_root/scripts/install.sh --pi --project "$project" --dry-run)
case "$pi_dry_run" in *'result: "dry-run"'*"$project/.pi/skills/braintree"*) ;; *) exit 1;; esac
[ ! -e "$project/.pi" ]

$repo_root/scripts/install.sh --pi --project "$project" >/dev/null
pi_destination="$project/.pi/skills/braintree"
check_tree "$pi_destination"
check_record "$pi_destination"
[ ! -e "$pi_destination/agents" ]
run_installed "$pi_destination"

pi_repeat=$($repo_root/scripts/install.sh --pi --project "$project")
case "$pi_repeat" in *'result: "no-op"'*'agent: "pi"'*) ;; *) exit 1;; esac

$repo_root/scripts/install.sh --pi --home "$home_root" >/dev/null
cmp -s "$repo_root/SKILL.md" "$home_root/.pi/agent/skills/braintree/SKILL.md"
[ ! -e "$home_root/.pi/agent/skills/braintree/agents" ]

$repo_root/scripts/install.sh --claude --project "$project" >/dev/null
claude_destination="$project/.claude/skills/braintree"
check_tree "$claude_destination"
check_record "$claude_destination"
[ ! -e "$claude_destination/agents" ]
run_installed "$claude_destination"

$repo_root/scripts/install.sh --claude --home "$home_root" >/dev/null
cmp -s "$repo_root/SKILL.md" "$home_root/.claude/skills/braintree/SKILL.md"
[ ! -e "$home_root/.claude/skills/braintree/agents" ]

claude_project="$test_root/claude-project"
claude_home="$test_root/claude-home"
mkdir -p "$claude_project" "$claude_home"

claude_dry_run=$($repo_root/scripts/install-claude.sh --project "$claude_project" --dry-run)
case "$claude_dry_run" in *'result: "dry-run"'*"$claude_project/.claude/skills/braintree"*) ;; *) exit 1;; esac
[ ! -e "$claude_project/.claude" ]
[ ! -e "$claude_project/.local" ]

$repo_root/scripts/install-claude.sh --project "$claude_project" >/dev/null
wrapper_destination="$claude_project/.claude/skills/braintree"
check_tree "$wrapper_destination"
check_record "$wrapper_destination"
[ ! -e "$wrapper_destination/agents" ]
run_installed "$wrapper_destination"
check_launcher "$claude_project"
claude_repeat=$($repo_root/scripts/install-claude.sh --project "$claude_project")
case "$claude_repeat" in *'result: "no-op"'*'agent: "claude"'*) ;; *) exit 1;; esac

$repo_root/scripts/install-claude.sh --home "$claude_home" >/dev/null
check_tree "$claude_home/.claude/skills/braintree"
check_record "$claude_home/.claude/skills/braintree"
[ ! -e "$claude_home/.claude/skills/braintree/agents" ]

if $repo_root/scripts/install.sh --codex >/dev/null 2>&1; then exit 1; fi
if $repo_root/scripts/install.sh --codex --project "$project" --unknown >/dev/null 2>&1; then exit 1; fi
error=$($repo_root/scripts/install.sh --codex 2>/dev/null || true)
case "$error" in *'error: "agent and destination scope are required"'*) ;; *) exit 1;; esac
for installer in "$repo_root/scripts/install.sh" "$repo_root/scripts/install-claude.sh"; do
  for flag in --version -v -V; do
    [ "$("$installer" "$flag")" = "$expected_version" ]
    if "$installer" "$flag" extra >/dev/null 2>&1; then exit 1; fi
    mixed=$("$installer" "$flag" extra 2>/dev/null || true)
    case "$mixed" in *'error: "unknown argument: '*) ;; *) exit 1;; esac
  done
done

help=$($repo_root/scripts/install.sh --help)
for expected in 'options[9]{flag,meaning}:' 'claude_wrapper: "scripts/install-claude.sh omits --claude and accepts the same destination flags."' 'launcher: "DIR/.local/bin/braintree, the single documented entry point"' '"--help, -h"' '"--version"' '"-v, -V"' 'examples[4]{command,purpose}:' '--codex --project /path/to/project --dry-run' '--claude --project /path/to/project' '--pi --project /path/to/project' '--codex --home $HOME'; do
  case "$help" in *"$expected"*) ;; *) exit 1;; esac
done

claude_help=$($repo_root/scripts/install-claude.sh --help)
for expected in 'usage: "scripts/install-claude.sh (--project DIR | --home DIR) [--dry-run]"' 'launcher: "DIR/.local/bin/braintree, the single documented entry point"' 'options[6]{flag,meaning}:' 'examples[3]{command,purpose}:' './scripts/install-claude.sh --project /path/to/project --dry-run' './scripts/install-claude.sh --home $HOME'; do
  case "$claude_help" in *"$expected"*) ;; *) exit 1;; esac
done
case "$claude_help" in *'--claude'*|*'--codex'*|*'--pi'*) exit 1;; esac
if $repo_root/scripts/install-claude.sh --codex --project "$claude_project" >/dev/null 2>&1; then exit 1; fi
claude_error=$($repo_root/scripts/install-claude.sh --unknown 2>/dev/null || true)
case "$claude_error" in *'error: "unknown argument: --unknown"'*'help: "scripts/install-claude.sh --project <directory> [--dry-run]"'*) ;; *) exit 1;; esac
case "$claude_error" in *'--claude'*|*'--codex'*|*'--pi'*) exit 1;; esac
claude_missing=$($repo_root/scripts/install-claude.sh --project 2>/dev/null || true)
case "$claude_missing" in *'error: "--project requires a directory"'*'help: "scripts/install-claude.sh --project <directory> [--dry-run]"'*) ;; *) exit 1;; esac

printf 'install tests: passed\n'
