#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM

project="$test_root/project"
home_root="$test_root/home"
mkdir -p "$project" "$home_root"

# uv keeps its cache under HOME, so each throwaway home below would pay a cold
# cache rebuild on its first install. One shared cache keeps the installer
# screens fast while still installing into a fresh home.
export UV_CACHE_DIR="${UV_CACHE_DIR:-$test_root/uv-cache}"

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
for file in "$repo_root"/src/tangle/*; do
  [ -f "$file" ] || continue
  program_files="$program_files src/tangle/$(basename -- "$file")"
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
  [ "$(cat "$program/src/tangle/installed-revision")" = "$expected_record" ]
}

# The one spelling of the stationary canonical layout. A storage change edits
# this helper, not the assertions that consume it: the shard is the identity's
# last two characters, and the immutable id is prefixed to the slug.
canonical_file() {
  _vault=$1
  _node_id=$2
  _slug=$3
  printf '%s/.tangle/canonical/%s/%s-%s.md\n' \
    "$_vault" "${_node_id#"${_node_id%??}"}" "$_node_id" "$_slug"
}

# Every install writes the single `tangle` command to <root>/.local/bin; it
# runs the shared program and exposes the same revision as that program.
check_launcher() {
  launcher="$1/.local/bin/tangle"
  [ -x "$launcher" ]
  [ "$("$launcher" --version)" = "$expected_record" ]
  # A read-only command must run the prepared program environment directly and
  # never initialize a uv cache: sandboxes commonly deny the user-home cache,
  # and uv run initializes it before dispatching. An unwritable UV_CACHE_DIR
  # proves the launcher did not fall back to uv run.
  read_only_cache=$(mktemp -d "$test_root/uv-cache.XXXXXX")
  chmod 0500 "$read_only_cache"
  rendered=$(UV_CACHE_DIR="$read_only_cache" "$launcher" help authoring 2>&1) || rendered=
  chmod 0700 "$read_only_cache"
  rm -rf "$read_only_cache"
  case "$rendered" in *'# Authoring reference'*) ;; *) exit 1;; esac
}

run_installed() {
  program=$1
  uv run --project "$program" --frozen --quiet tangle check "$repo_root/.tangle" >/dev/null
  uv run --project "$program" --frozen --quiet tangle feedback scan "$repo_root/.tangle" >/dev/null
  [ "$(uv run --project "$program" --frozen --quiet tangle --version)" = "$expected_record" ]
  run_installed_help "$program"
  run_installed_feedback_record "$program"
  run_installed_research_boundary "$program"
}

# A default installed program contains only the core package. Its retired
# behavioral command explains the repository-only path without probing,
# importing, or installing research implementation on demand.
run_installed_research_boundary() {
  program=$1
  probe_cwd=$(mktemp -d "$test_root/research-boundary.XXXXXX")
  (cd "$probe_cwd" && uv run --project "$program" --frozen --quiet python -c \
    'import importlib.util as u; assert u.find_spec("tangle_research") is None; assert u.find_spec("tangle.behavioral_benchmark") is None; assert u.find_spec("tangle.verb_benchmark") is None')
  unavailable=$(cd "$probe_cwd" && uv run --project "$program" --frozen --quiet \
    tangle benchmark behavioral 2>&1 || true)
  case "$unavailable" in
    *'unavailable in an ordinary installation'*'make diagnostic-benchmark'*) ;;
    *) exit 1 ;;
  esac
  unavailable=$(cd "$probe_cwd" && uv run --project "$program" --frozen --quiet \
    tangle benchmark verb 2>&1 || true)
  case "$unavailable" in
    *'unavailable in an ordinary installation'*'PYTHONPATH=research uv run python -m tangle_research.verb_benchmark'*) ;;
    *) exit 1 ;;
  esac
  rm -rf "$probe_cwd"
}

# The shared program's reference tree must be installed and rendered by the
# installed command, without a vault and without initializing the sidecar.
run_installed_help() {
  program=$1
  help_cwd=$(mktemp -d "$test_root/help.XXXXXX")
  # One topic proves the installed reference tree renders; the remaining topics
  # are covered by the pytest suite.
  rendered=$(cd "$help_cwd" && uv run --project "$program" --frozen --quiet \
    tangle help coordination)
  case "$rendered" in *coordination*) ;; *) exit 1;; esac
  [ ! -e "$help_cwd/.tangle" ]
  rm -rf "$help_cwd"
}

# The recording half of the feedback mechanism must work from an installed
# skill in a consuming project, not only from this source repository.
run_installed_feedback_record() {
  program=$1
  vault=$(mktemp -d "$test_root/feedback.XXXXXX")
  # A deterministic id and slug make the written path predictable through the
  # shared canonical_file helper instead of a shard-glob assumption.
  record_id=fbk-00000000000000000000000001
  record_slug=installed-command
  mkdir -p "$vault/.tangle"
  cat >"$vault/.tangle/index-map.md" <<'EOF'
# Root hubs

- Indexes [[IDX-001-root]]
EOF
  hub=$(canonical_file "$vault" IDX-001 root)
  mkdir -p "$(dirname -- "$hub")"
  cat >"$hub" <<'EOF'
---
status: resolved
context_rev: 1
updated: 2026-09-12T00:00:00Z
summary: Root hub.
---
EOF
  uv run --project "$program" --frozen --quiet tangle feedback record \
    --nodes "$vault/.tangle" \
    --id "$record_id" \
    --slug "$record_slug" \
    --attempted 'Ran the installed command.' \
    --friction 'The installed recording path was untested.' \
    --improvement 'Exercise it in the install test.' >/dev/null
  uv run --project "$program" --frozen --quiet tangle check "$vault/.tangle" >/dev/null
  grep -q "tangle_revision: $expected_record" \
    "$(canonical_file "$vault" "$record_id" "$record_slug")"
  rm -rf "$vault"
}

dry_run=$($repo_root/scripts/install.sh --codex --project "$project" --dry-run)
case "$dry_run" in *"$project/.agents/skills/tangle"*) ;; *) exit 1;; esac
case "$dry_run" in *"program: \"$project/.local/share/tangle\""*) ;; *) exit 1;; esac
[ ! -e "$project/.agents" ]
[ ! -e "$project/.local" ]

$repo_root/scripts/install.sh --codex --project "$project" >/dev/null
codex_destination="$project/.agents/skills/tangle"
check_prose "$codex_destination"
cmp -s "$repo_root/agents/openai.yaml" "$codex_destination/agents/openai.yaml"
program_dir="$project/.local/share/tangle"
check_program "$program_dir"
check_record "$program_dir"
run_installed "$program_dir"
check_launcher "$project"

launcher_path="$project/.local/bin/tangle"
program_record_path="$program_dir/src/tangle/installed-revision"
repeat=$($repo_root/scripts/install.sh --codex --project "$project")
case "$repeat" in *'result: "no-op"'*) ;; *) exit 1;; esac
[ "$(cat "$program_record_path")" = "$expected_record" ]

# Upgrading an installation made before the research split removes the retired
# in-package implementation instead of leaving it importable indefinitely.
printf '%s\n' 'stale behavioral implementation' >"$program_dir/src/tangle/behavioral_benchmark.py"
printf '%s\n' 'stale verb implementation' >"$program_dir/src/tangle/verb_benchmark.py"
stale_upgrade=$($repo_root/scripts/install.sh --codex --project "$project")
case "$stale_upgrade" in *'result: "installed"'*) ;; *) exit 1;; esac
[ ! -e "$program_dir/src/tangle/behavioral_benchmark.py" ]
[ ! -e "$program_dir/src/tangle/verb_benchmark.py" ]
run_installed_research_boundary "$program_dir"

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

$repo_root/scripts/install.sh --codex --home "$home_root" >/dev/null
check_prose "$home_root/.agents/skills/tangle"
check_program "$home_root/.local/share/tangle"
check_record "$home_root/.local/share/tangle"
check_launcher "$home_root"

pi_dry_run=$($repo_root/scripts/install.sh --pi --project "$project" --dry-run)
case "$pi_dry_run" in *'result: "dry-run"'*"$project/.pi/skills/tangle"*) ;; *) exit 1;; esac
[ ! -e "$project/.pi" ]

$repo_root/scripts/install.sh --pi --project "$project" >/dev/null
pi_destination="$project/.pi/skills/tangle"
check_prose "$pi_destination"
[ ! -e "$pi_destination/agents" ]

pi_repeat=$($repo_root/scripts/install.sh --pi --project "$project")
case "$pi_repeat" in *'result: "no-op"'*'agent: "pi"'*) ;; *) exit 1;; esac

$repo_root/scripts/install.sh --pi --home "$home_root" >/dev/null
check_prose "$home_root/.pi/agent/skills/tangle"
[ ! -e "$home_root/.pi/agent/skills/tangle/agents" ]

$repo_root/scripts/install.sh --claude --project "$project" >/dev/null
claude_destination="$project/.claude/skills/tangle"
check_prose "$claude_destination"
[ ! -e "$claude_destination/agents" ]

# Installing another agent into the same root does not repoint the shared
# command: the launcher target and the shared program revision are unchanged.
[ "$(cat "$launcher_path")" = "$launcher_snapshot" ]
[ "$(cat "$program_record_path")" = "$program_snapshot" ]
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
check_prose "$home_root/.claude/skills/tangle"
[ ! -e "$home_root/.claude/skills/tangle/agents" ]

claude_project="$test_root/claude-project"
claude_home="$test_root/claude-home"
mkdir -p "$claude_project" "$claude_home"

claude_dry_run=$($repo_root/scripts/install-claude.sh --project "$claude_project" --dry-run)
case "$claude_dry_run" in *'result: "dry-run"'*"$claude_project/.claude/skills/tangle"*) ;; *) exit 1;; esac
[ ! -e "$claude_project/.claude" ]
[ ! -e "$claude_project/.local" ]

$repo_root/scripts/install-claude.sh --project "$claude_project" >/dev/null
wrapper_destination="$claude_project/.claude/skills/tangle"
check_prose "$wrapper_destination"
check_program "$claude_project/.local/share/tangle"
check_record "$claude_project/.local/share/tangle"
[ ! -e "$wrapper_destination/agents" ]
run_installed "$claude_project/.local/share/tangle"
check_launcher "$claude_project"
claude_repeat=$($repo_root/scripts/install-claude.sh --project "$claude_project")
case "$claude_repeat" in *'result: "no-op"'*'agent: "claude"'*) ;; *) exit 1;; esac

$repo_root/scripts/install-claude.sh --home "$claude_home" >/dev/null
check_prose "$claude_home/.claude/skills/tangle"
check_program "$claude_home/.local/share/tangle"
check_record "$claude_home/.local/share/tangle"
[ ! -e "$claude_home/.claude/skills/tangle/agents" ]

# An explicit --semantic install requests the optional extra and defaults the
# provider, so the installed capability is zero-config; a plain install keeps the
# launcher on the dependency-free frozen set. A fake uv stands in for both the
# install-time environment sync and the launcher's fallback, reading the
# launcher's environment without syncing the extra, keeping this offline.
fake_bin="$test_root/fake-bin"
mkdir -p "$fake_bin"
cat > "$fake_bin/uv" <<'FAKE_UV'
#!/bin/sh
case "${TANGLE_SEMANTIC_PROVIDER+x}" in
  x) printf 'provider=[%s]\n' "$TANGLE_SEMANTIC_PROVIDER" ;;
  *) printf 'provider=<unset>\n' ;;
esac
FAKE_UV
chmod 0755 "$fake_bin/uv"

semantic_project="$test_root/semantic-project"
mkdir -p "$semantic_project"
PATH="$fake_bin:$PATH" "$repo_root/scripts/install.sh" --codex --project "$semantic_project" >/dev/null
semantic_launcher="$semantic_project/.local/bin/tangle"
if grep -q -- '--extra semantic' "$semantic_launcher"; then exit 1; fi
plain_env=$(unset TANGLE_SEMANTIC_PROVIDER; PATH="$fake_bin:$PATH" "$semantic_launcher")
case "$plain_env" in *'provider=<unset>'*) ;; *) exit 1;; esac
semantic_install=$(PATH="$fake_bin:$PATH" "$repo_root/scripts/install.sh" --codex --project "$semantic_project" --semantic)
case "$semantic_install" in
  *'result: "installed"'*'provider: "defaults to tangle semantic embed'*) ;;
  *) exit 1 ;;
esac
grep -q -- '--frozen --extra semantic tangle "$@"' "$semantic_launcher"
semantic_default=$(unset TANGLE_SEMANTIC_PROVIDER; PATH="$fake_bin:$PATH" "$semantic_launcher")
case "$semantic_default" in *'provider=[tangle semantic embed]'*) ;; *) exit 1;; esac
semantic_override=$(unset TANGLE_SEMANTIC_PROVIDER; PATH="$fake_bin:$PATH" TANGLE_SEMANTIC_PROVIDER='custom provider' "$semantic_launcher")
case "$semantic_override" in *'provider=[custom provider]'*) ;; *) exit 1;; esac
semantic_empty=$(unset TANGLE_SEMANTIC_PROVIDER; PATH="$fake_bin:$PATH" TANGLE_SEMANTIC_PROVIDER='' "$semantic_launcher")
case "$semantic_empty" in *'provider=[]'*) ;; *) exit 1;; esac
[ "$(cat "$semantic_project/.local/share/tangle/src/tangle/installed-revision")" = "$expected_record" ]
semantic_repeat=$(PATH="$fake_bin:$PATH" "$repo_root/scripts/install.sh" --codex --project "$semantic_project" --semantic)
case "$semantic_repeat" in *'result: "no-op"'*) ;; *) exit 1;; esac

if $repo_root/scripts/install.sh --codex --project "$project" --unknown >/dev/null 2>&1; then exit 1; fi
# An omitted destination scope now defaults to the home root, so a lone agent
# flag is a supported non-interactive install.
default_home="$test_root/default-home"
mkdir -p "$default_home"
default_out=$(HOME="$default_home" $repo_root/scripts/install.sh --codex)
case "$default_out" in *'result: "installed"'*'agent: "codex"'*"$default_home/.agents/skills/tangle"*) ;; *) exit 1;; esac
no_home=$(env -u HOME "$repo_root/scripts/install.sh" 2>/dev/null || true)
case "$no_home" in *'error: "no home root: set HOME or pass --project DIR"'*) ;; *) exit 1;; esac
for installer in "$repo_root/scripts/install.sh" "$repo_root/scripts/install-claude.sh"; do
  for flag in --version -v -V; do
    [ "$("$installer" "$flag")" = "$expected_version" ]
    if "$installer" "$flag" extra >/dev/null 2>&1; then exit 1; fi
    mixed=$("$installer" "$flag" extra 2>/dev/null || true)
    case "$mixed" in *'error: "unknown argument: '*) ;; *) exit 1;; esac
  done
done

help=$($repo_root/scripts/install.sh --help)
# The usage line and every documented flag must appear; the exact option count,
# field names, and example lines are presentation, not a user guarantee.
for expected in 'usage: "scripts/install.sh' '"--codex"' '"--claude"' '"--pi"' '"--project DIR"' '"--home DIR"' '"--select"' '"--dry-run"' '"--semantic"' '"--help, -h"' '"--version"' '"-v, -V"'; do
  case "$help" in *"$expected"*) ;; *) exit 1;; esac
done

claude_help=$($repo_root/scripts/install-claude.sh --help)
for expected in 'usage: "scripts/install-claude.sh' '"--project DIR"' '"--home DIR"' '"--dry-run"' '"--semantic"' '"--help, -h"' '"--version"' '"-v, -V"'; do
  case "$claude_help" in *"$expected"*) ;; *) exit 1;; esac
done
case "$claude_help" in *'--claude'*|*'--codex'*|*'--pi'*) exit 1;; esac
if $repo_root/scripts/install-claude.sh --codex --project "$claude_project" >/dev/null 2>&1; then exit 1; fi
claude_error=$($repo_root/scripts/install-claude.sh --unknown 2>/dev/null || true)
case "$claude_error" in *'error: "unknown argument: --unknown"'*'help: "scripts/install-claude.sh --project <directory> [--dry-run]"'*) ;; *) exit 1;; esac
case "$claude_error" in *'--claude'*|*'--codex'*|*'--pi'*) exit 1;; esac
claude_missing=$($repo_root/scripts/install-claude.sh --project 2>/dev/null || true)
case "$claude_missing" in *'error: "--project requires a directory"'*'help: "scripts/install-claude.sh --project <directory> [--dry-run]"'*) ;; *) exit 1;; esac

# A bare invocation is the zero-config install: the shared command and every
# supported agent skill land in the home root, with no menu and no terminal.
zero_home="$test_root/zero-home"
mkdir -p "$zero_home"
zero_output=$(HOME="$zero_home" "$repo_root/scripts/install.sh" </dev/null)
case "$zero_output" in *'result: "installed"'*'selected: "3"'*'scope: "home"'*) ;; *) exit 1;; esac
case "$zero_output" in *'outcomes[3]{agent,destination,program,launcher,result}:'*) ;; *) exit 1;; esac
for expected in \
  "\"codex\",\"$zero_home/.agents/skills/tangle\"" \
  "\"claude\",\"$zero_home/.claude/skills/tangle\"" \
  "\"pi\",\"$zero_home/.pi/agent/skills/tangle\""; do
  case "$zero_output" in *"$expected"*) ;; *) exit 1;; esac
done
check_prose "$zero_home/.agents/skills/tangle"
check_prose "$zero_home/.claude/skills/tangle"
check_prose "$zero_home/.pi/agent/skills/tangle"
check_program "$zero_home/.local/share/tangle"
check_record "$zero_home/.local/share/tangle"
check_launcher "$zero_home"

# Re-running the zero-config install is a no-op, and an omitted agent with an
# explicit project root installs every agent there.
zero_repeat=$(HOME="$zero_home" "$repo_root/scripts/install.sh" </dev/null)
case "$zero_repeat" in *'result: "no-op"'*'selected: "3"'*) ;; *) exit 1;; esac
zero_project="$test_root/zero-project"
mkdir -p "$zero_project"
zero_project_output=$(HOME="$zero_home" "$repo_root/scripts/install.sh" --project "$zero_project" </dev/null)
case "$zero_project_output" in *'result: "installed"'*'scope: "project"'*"$zero_project/.pi/skills/tangle"*) ;; *) exit 1;; esac
check_launcher "$zero_project"

# --select opts into the interactive selector and cannot be combined with an
# explicit agent or destination.
if (HOME="$zero_home" "$repo_root/scripts/install.sh" --select --pi </dev/null) >/dev/null 2>&1; then exit 1; fi
zero_conflict=$(HOME="$zero_home" "$repo_root/scripts/install.sh" --select --pi </dev/null 2>/dev/null || true)
case "$zero_conflict" in *'error: "--select cannot be combined with an agent or destination"'*) ;; *) exit 1;; esac

# --select discovers the enclosing project root and the home root, crosses them
# with the supported agents, and installs every selected target.
# TANGLE_INSTALL_SELECTION supplies the selection so the multi-select path runs
# without a terminal; the menu it replaces is asserted through the same output.
selector_project="$test_root/selector-project"
selector_home="$test_root/selector-home"
mkdir -p "$selector_project/.git" "$selector_home"

selector_output=$(cd "$selector_project" && HOME="$selector_home" TANGLE_INSTALL_SELECTION='1,4' \
  "$repo_root/scripts/install.sh" --select </dev/null)
case "$selector_output" in *'result: "menu"'*) ;; *) exit 1;; esac
case "$selector_output" in *'targets[6]{index,agent,root,destination}:'*) ;; *) exit 1;; esac
for expected in \
  "\"1\",\"codex\",\"$selector_project\",\"$selector_project/.agents/skills/tangle\"" \
  "\"2\",\"claude\",\"$selector_project\",\"$selector_project/.claude/skills/tangle\"" \
  "\"3\",\"pi\",\"$selector_project\",\"$selector_project/.pi/skills/tangle\"" \
  "\"4\",\"codex\",\"$selector_home\",\"$selector_home/.agents/skills/tangle\"" \
  "\"5\",\"claude\",\"$selector_home\",\"$selector_home/.claude/skills/tangle\"" \
  "\"6\",\"pi\",\"$selector_home\",\"$selector_home/.pi/agent/skills/tangle\""; do
  case "$selector_output" in *"$expected"*) ;; *) exit 1;; esac
done
case "$selector_output" in *'result: "multi"'*'selected: "2"'*'outcomes[2]{agent,destination,program,launcher,result}:'*) ;; *) exit 1;; esac
case "$selector_output" in *'"installed"'*'"installed"'*) ;; *) exit 1;; esac

# Only the selected targets are installed, and each selected one carries both
# the skill prose and the shared per-root command.
check_prose "$selector_project/.agents/skills/tangle"
check_prose "$selector_home/.agents/skills/tangle"
check_program "$selector_project/.local/share/tangle"
check_record "$selector_project/.local/share/tangle"
check_launcher "$selector_project"
check_launcher "$selector_home"
[ ! -e "$selector_project/.claude" ]
[ ! -e "$selector_project/.pi" ]
[ ! -e "$selector_home/.claude" ]
[ ! -e "$selector_home/.pi" ]

# Re-selecting the same targets is a no-op for each outcome, and a space
# separated selection parses like the comma separated one.
selector_repeat=$(cd "$selector_project" && HOME="$selector_home" TANGLE_INSTALL_SELECTION='1 4' \
  "$repo_root/scripts/install.sh" --select </dev/null)
case "$selector_repeat" in *'selected: "2"'*'"no-op"'*'"no-op"'*) ;; *) exit 1;; esac
[ ! -e "$selector_project/.claude" ]

# "all" selects every discovered target; an empty selection cancels without
# installing.
selector_all=$(cd "$selector_project" && HOME="$selector_home" TANGLE_INSTALL_SELECTION='all' \
  "$repo_root/scripts/install.sh" --select </dev/null)
case "$selector_all" in *'selected: "6"'*) ;; *) exit 1;; esac
check_prose "$selector_project/.claude/skills/tangle"
check_prose "$selector_project/.pi/skills/tangle"
selector_empty=$(cd "$selector_project" && HOME="$selector_home" TANGLE_INSTALL_SELECTION='' \
  "$repo_root/scripts/install.sh" --select </dev/null)
case "$selector_empty" in *'result: "cancelled"'*) ;; *) exit 1;; esac

# A cancelled selection installs nothing into a fresh root.
selector_cancel_project="$test_root/selector-cancel-project"
selector_cancel_home="$test_root/selector-cancel-home"
mkdir -p "$selector_cancel_project/.git" "$selector_cancel_home"
selector_cancel=$(cd "$selector_cancel_project" && HOME="$selector_cancel_home" TANGLE_INSTALL_SELECTION='' \
  "$repo_root/scripts/install.sh" --select </dev/null)
case "$selector_cancel" in *'result: "cancelled"'*) ;; *) exit 1;; esac
[ ! -e "$selector_cancel_project/.local" ]
[ ! -e "$selector_cancel_project/.agents" ]
[ ! -e "$selector_cancel_home/.local" ]

# An interactive --dry-run reports every selected destination and writes nothing.
selector_dry_project="$test_root/selector-dry-project"
selector_dry_home="$test_root/selector-dry-home"
mkdir -p "$selector_dry_project/.git"
selector_dry=$(cd "$selector_dry_project" && HOME="$selector_dry_home" TANGLE_INSTALL_SELECTION='1' \
  "$repo_root/scripts/install.sh" --select --dry-run </dev/null)
case "$selector_dry" in *'outcomes[1]'*'"dry-run"'*) ;; *) exit 1;; esac
[ ! -e "$selector_dry_project/.agents" ]
[ ! -e "$selector_dry_project/.local" ]

# An invalid selection and an out-of-range number fail clearly.
if (cd "$selector_project" && HOME="$selector_home" TANGLE_INSTALL_SELECTION='x' \
  "$repo_root/scripts/install.sh" --select </dev/null) >/dev/null 2>&1; then exit 1; fi
selector_invalid=$(cd "$selector_project" && HOME="$selector_home" TANGLE_INSTALL_SELECTION='x' \
  "$repo_root/scripts/install.sh" --select </dev/null 2>/dev/null || true)
case "$selector_invalid" in *'error: "invalid selection: x"'*) ;; *) exit 1;; esac
selector_range=$(cd "$selector_project" && HOME="$selector_home" TANGLE_INSTALL_SELECTION='9' \
  "$repo_root/scripts/install.sh" --select </dev/null 2>/dev/null || true)
case "$selector_range" in *'error: "selection out of range: 9"'*) ;; *) exit 1;; esac

# A bare --select never prompts on a non-terminal stdin and never hangs, so an
# automated run stays deterministic.
if (cd "$selector_project" && HOME="$selector_home" "$repo_root/scripts/install.sh" --select </dev/null) >/dev/null 2>&1; then exit 1; fi
selector_error=$(cd "$selector_project" && HOME="$selector_home" "$repo_root/scripts/install.sh" --select </dev/null 2>/dev/null || true)
case "$selector_error" in *'error: "no install target: a bare --select needs a terminal'*) ;; *) exit 1;; esac

# The explicit flags stay the non-interactive contract: with the same
# non-terminal stdin they install without presenting a menu.
selector_flagged=$(cd "$selector_project" && "$repo_root/scripts/install.sh" --codex --project "$selector_project" </dev/null)
case "$selector_flagged" in *'result: "no-op"'*'agent: "codex"'*) ;; *) exit 1;; esac
case "$selector_flagged" in *'result: "menu"'*) exit 1;; esac

printf 'install tests: passed\n'
