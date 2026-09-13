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

# One shared program per root runs the installed command and carries the package
# tree, its metadata, the reference tree the command renders, and the generated
# install record. Every agent destination is only the skill prose the agent
# discovers, so an agent install never duplicates or repoints the program.
program_files="pyproject.toml uv.lock .python-version README.md"
for file in "$repo_root"/src/braintree/*; do
  [ -f "$file" ] || continue
  program_files="$program_files src/braintree/$(basename -- "$file")"
done
for file in "$repo_root"/references/*.md; do
  [ -f "$file" ] || continue
  program_files="$program_files references/$(basename -- "$file")"
done

check_program() {
  program=$1
  for relative in $program_files; do
    cmp -s "$repo_root/$relative" "$program/$relative"
  done
  # The program is the runnable distribution, not the agent-facing prose copy.
  [ ! -e "$program/SKILL.md" ]
}

# The agent destination holds the skill prose and no second program copy.
check_prose() {
  destination=$1
  cmp -s "$repo_root/SKILL.md" "$destination/SKILL.md"
  for file in "$repo_root"/references/*.md; do
    [ -f "$file" ] || continue
    cmp -s "$file" "$destination/references/$(basename -- "$file")"
  done
  [ ! -e "$destination/pyproject.toml" ]
  [ ! -e "$destination/uv.lock" ]
  [ ! -e "$destination/src" ]
}

check_record() {
  program=$1
  [ "$(cat "$program/src/braintree/installed-revision")" = "$expected_record" ]
}

mtime() {
  stat -f %m "$1" 2>/dev/null || stat -c %Y "$1"
}

# Every install writes the single `braintree` command to <root>/.local/bin; it
# runs the shared program and exposes the same revision as that program.
check_launcher() {
  launcher="$1/.local/bin/braintree"
  [ -x "$launcher" ]
  [ "$("$launcher" --version)" = "$expected_record" ]
}

run_installed() {
  program=$1
  uv run --project "$program" --frozen --quiet braintree check "$repo_root/.braintree" >/dev/null
  uv run --project "$program" --frozen --quiet braintree feedback scan "$repo_root/.braintree" >/dev/null
  [ "$(uv run --project "$program" --frozen --quiet braintree --version)" = "$expected_record" ]
  run_installed_help "$program"
  run_installed_feedback_record "$program"
}

# The shared program's reference tree must be installed and rendered by the
# installed command, without a vault and without initializing the sidecar.
run_installed_help() {
  program=$1
  help_cwd=$(mktemp -d "$test_root/help.XXXXXX")
  for topic in coordination dependencies authoring; do
    rendered=$(cd "$help_cwd" && uv run --project "$program" --frozen --quiet \
      braintree help "$topic")
    case "$rendered" in *"$topic"*) ;; *) exit 1;; esac
  done
  [ ! -e "$help_cwd/.braintree" ]
  rm -rf "$help_cwd"
}

# The recording half of the feedback mechanism must work from an installed
# skill in a consuming project, not only from this source repository.
run_installed_feedback_record() {
  program=$1
  vault=$(mktemp -d "$test_root/feedback.XXXXXX")
  mkdir -p "$vault/.braintree/resolved"
  cat >"$vault/.braintree/index-map.md" <<'EOF'
# Root hubs

- Indexes [[IDX-001-root]]
EOF
  cat >"$vault/.braintree/resolved/IDX-001-root.md" <<'EOF'
---
context_rev: 1
updated: 2026-09-12T00:00:00Z
summary: Root hub.
---
EOF
  uv run --project "$program" --frozen --quiet braintree feedback record \
    --nodes "$vault/.braintree" \
    --attempted 'Ran the installed command.' \
    --friction 'The installed recording path was untested.' \
    --improvement 'Exercise it in the install test.' >/dev/null
  uv run --project "$program" --frozen --quiet braintree check "$vault/.braintree" >/dev/null
  grep -q "braintree_revision: $expected_record" "$vault"/.braintree/proposed/FBK-001-*.md
  rm -rf "$vault"
}

dry_run=$($repo_root/scripts/install.sh --codex --project "$project" --dry-run)
case "$dry_run" in *"$project/.agents/skills/braintree"*) ;; *) exit 1;; esac
case "$dry_run" in *"program: \"$project/.local/share/braintree\""*) ;; *) exit 1;; esac
[ ! -e "$project/.agents" ]
[ ! -e "$project/.local" ]

$repo_root/scripts/install.sh --codex --project "$project" >/dev/null
codex_destination="$project/.agents/skills/braintree"
check_prose "$codex_destination"
cmp -s "$repo_root/agents/openai.yaml" "$codex_destination/agents/openai.yaml"
program_dir="$project/.local/share/braintree"
check_program "$program_dir"
check_record "$program_dir"
run_installed "$program_dir"
check_launcher "$project"

launcher_path="$project/.local/bin/braintree"
program_record_path="$program_dir/src/braintree/installed-revision"
record_mtime=$(mtime "$program_record_path")
launcher_mtime=$(mtime "$launcher_path")
repeat=$($repo_root/scripts/install.sh --codex --project "$project")
case "$repeat" in *'result: "no-op"'*) ;; *) exit 1;; esac
[ "$(cat "$program_record_path")" = "$expected_record" ]
[ "$(mtime "$program_record_path")" = "$record_mtime" ]
[ "$(mtime "$launcher_path")" = "$launcher_mtime" ]

# A changed installed revision is detected and restamped, not reported no-op.
printf '%s\n' '0.0.0+gold' >"$program_record_path"
upgrade=$($repo_root/scripts/install.sh --codex --project "$project")
case "$upgrade" in *'result: "installed"'*) ;; *) exit 1;; esac
check_record "$program_dir"

# A reference-only change is detected and restored, not reported no-op, and the
# restored tree returns to a clean no-op on the next run.
printf '%s\n' 'stale reference prose' >"$codex_destination/references/coordination.md"
reference_upgrade=$($repo_root/scripts/install.sh --codex --project "$project")
case "$reference_upgrade" in *'result: "installed"'*) ;; *) exit 1;; esac
cmp -s "$repo_root/references/coordination.md" "$codex_destination/references/coordination.md"
reference_repeat=$($repo_root/scripts/install.sh --codex --project "$project")
case "$reference_repeat" in *'result: "no-op"'*) ;; *) exit 1;; esac

# Snapshot the shared command and program before installing other agents into
# the same root; a per-agent install must leave both untouched.
launcher_snapshot=$(cat "$launcher_path")
program_snapshot=$(cat "$program_record_path")
launcher_mtime=$(mtime "$launcher_path")
program_mtime=$(mtime "$program_record_path")

$repo_root/scripts/install.sh --codex --home "$home_root" >/dev/null
check_prose "$home_root/.agents/skills/braintree"
check_program "$home_root/.local/share/braintree"
check_record "$home_root/.local/share/braintree"
check_launcher "$home_root"

pi_dry_run=$($repo_root/scripts/install.sh --pi --project "$project" --dry-run)
case "$pi_dry_run" in *'result: "dry-run"'*"$project/.pi/skills/braintree"*) ;; *) exit 1;; esac
[ ! -e "$project/.pi" ]

$repo_root/scripts/install.sh --pi --project "$project" >/dev/null
pi_destination="$project/.pi/skills/braintree"
check_prose "$pi_destination"
[ ! -e "$pi_destination/agents" ]
run_installed "$program_dir"

pi_repeat=$($repo_root/scripts/install.sh --pi --project "$project")
case "$pi_repeat" in *'result: "no-op"'*'agent: "pi"'*) ;; *) exit 1;; esac

$repo_root/scripts/install.sh --pi --home "$home_root" >/dev/null
check_prose "$home_root/.pi/agent/skills/braintree"
[ ! -e "$home_root/.pi/agent/skills/braintree/agents" ]

$repo_root/scripts/install.sh --claude --project "$project" >/dev/null
claude_destination="$project/.claude/skills/braintree"
check_prose "$claude_destination"
[ ! -e "$claude_destination/agents" ]
run_installed "$program_dir"

# Installing another agent into the same root does not repoint the shared
# command: the launcher target and the shared program revision are unchanged.
[ "$(cat "$launcher_path")" = "$launcher_snapshot" ]
[ "$(mtime "$launcher_path")" = "$launcher_mtime" ]
[ "$(cat "$program_record_path")" = "$program_snapshot" ]
[ "$(mtime "$program_record_path")" = "$program_mtime" ]
case "$launcher_snapshot" in *"--project \"$program_dir\""*) ;; *) exit 1;; esac

# One program per root: no agent destination carries a program copy and the
# root holds exactly one installed-revision record.
[ "$(find "$project" -type f -name installed-revision | wc -l | tr -d ' ')" = 1 ]
for agent_destination in "$codex_destination" "$pi_destination" "$claude_destination"; do
  [ ! -e "$agent_destination/pyproject.toml" ]
  [ ! -e "$agent_destination/uv.lock" ]
  [ ! -e "$agent_destination/src" ]
done

$repo_root/scripts/install.sh --claude --home "$home_root" >/dev/null
check_prose "$home_root/.claude/skills/braintree"
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
check_prose "$wrapper_destination"
check_program "$claude_project/.local/share/braintree"
check_record "$claude_project/.local/share/braintree"
[ ! -e "$wrapper_destination/agents" ]
run_installed "$claude_project/.local/share/braintree"
check_launcher "$claude_project"
claude_repeat=$($repo_root/scripts/install-claude.sh --project "$claude_project")
case "$claude_repeat" in *'result: "no-op"'*'agent: "claude"'*) ;; *) exit 1;; esac

$repo_root/scripts/install-claude.sh --home "$claude_home" >/dev/null
check_prose "$claude_home/.claude/skills/braintree"
check_program "$claude_home/.local/share/braintree"
check_record "$claude_home/.local/share/braintree"
[ ! -e "$claude_home/.claude/skills/braintree/agents" ]

# An explicit --semantic install requests the optional extra and defaults the
# provider, so the installed capability is zero-config; a plain install keeps the
# launcher on the dependency-free frozen set. A fake uv reads the launcher's
# environment without syncing the extra, keeping this offline.
fake_bin="$test_root/fake-bin"
mkdir -p "$fake_bin"
cat > "$fake_bin/uv" <<'FAKE_UV'
#!/bin/sh
case "${BT_SEMANTIC_PROVIDER+x}" in
  x) printf 'provider=[%s]\n' "$BT_SEMANTIC_PROVIDER" ;;
  *) printf 'provider=<unset>\n' ;;
esac
FAKE_UV
chmod 0755 "$fake_bin/uv"

semantic_project="$test_root/semantic-project"
mkdir -p "$semantic_project"
$repo_root/scripts/install.sh --codex --project "$semantic_project" >/dev/null
semantic_launcher="$semantic_project/.local/bin/braintree"
if grep -q -- '--extra semantic' "$semantic_launcher"; then exit 1; fi
plain_env=$(unset BT_SEMANTIC_PROVIDER; PATH="$fake_bin:$PATH" "$semantic_launcher")
case "$plain_env" in *'provider=<unset>'*) ;; *) exit 1;; esac
semantic_install=$($repo_root/scripts/install.sh --codex --project "$semantic_project" --semantic)
case "$semantic_install" in
  *'result: "installed"'*'provider: "defaults to braintree semantic embed'*) ;;
  *) exit 1 ;;
esac
grep -q -- '--frozen --extra semantic braintree "$@"' "$semantic_launcher"
semantic_default=$(unset BT_SEMANTIC_PROVIDER; PATH="$fake_bin:$PATH" "$semantic_launcher")
case "$semantic_default" in *'provider=[braintree semantic embed]'*) ;; *) exit 1;; esac
semantic_override=$(unset BT_SEMANTIC_PROVIDER; PATH="$fake_bin:$PATH" BT_SEMANTIC_PROVIDER='custom provider' "$semantic_launcher")
case "$semantic_override" in *'provider=[custom provider]'*) ;; *) exit 1;; esac
semantic_empty=$(unset BT_SEMANTIC_PROVIDER; PATH="$fake_bin:$PATH" BT_SEMANTIC_PROVIDER='' "$semantic_launcher")
case "$semantic_empty" in *'provider=[]'*) ;; *) exit 1;; esac
[ "$(cat "$semantic_project/.local/share/braintree/src/braintree/installed-revision")" = "$expected_record" ]
semantic_repeat=$($repo_root/scripts/install.sh --codex --project "$semantic_project" --semantic)
case "$semantic_repeat" in *'result: "no-op"'*) ;; *) exit 1;; esac

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
for expected in 'options[10]{flag,meaning}:' 'claude_wrapper: "scripts/install-claude.sh omits --claude and accepts the same destination flags."' 'launcher: "DIR/.local/bin/braintree, the single documented entry point"' 'program: "DIR/.local/share/braintree, the one shared program per root the launcher runs"' '"--semantic"' '"--help, -h"' '"--version"' '"-v, -V"' 'examples[5]{command,purpose}:' '--codex --project /path/to/project --dry-run' '--claude --project /path/to/project' '--pi --project /path/to/project' '--pi --home $HOME --semantic' '--codex --home $HOME'; do
  case "$help" in *"$expected"*) ;; *) exit 1;; esac
done

claude_help=$($repo_root/scripts/install-claude.sh --help)
for expected in 'usage: "scripts/install-claude.sh (--project DIR | --home DIR) [--dry-run] [--semantic]"' 'launcher: "DIR/.local/bin/braintree, the single documented entry point"' 'program: "DIR/.local/share/braintree, the one shared program per root the launcher runs"' 'options[7]{flag,meaning}:' '"--semantic"' 'examples[4]{command,purpose}:' './scripts/install-claude.sh --project /path/to/project --dry-run' './scripts/install-claude.sh --home $HOME --semantic' './scripts/install-claude.sh --home $HOME'; do
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
