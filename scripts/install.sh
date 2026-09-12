#!/bin/sh
# Install this skill into an explicitly selected Codex, Claude Code, or pi location.
set -eu

# The project version is declared once in ``pyproject.toml``. Read it here so
# the installer and the installed package always report the same number.
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1
version=$(sed -n 's/^version *= *"\([^"]*\)".*/\1/p' "$repo_root/pyproject.toml" | head -n 1)
if [ -z "$version" ]; then
  printf '%s\n' 'error: "unable to read the project version from pyproject.toml"'
  exit 1
fi

skill_name=braintree
agent=
scope=
root=
dry_run=false
presentation=${BT_INSTALL_PRESENTATION:-generic}

if [ "$#" -eq 1 ]; then
  case "$1" in
    --version|-v|-V) printf '%s\n' "$version"; exit 0 ;;
  esac
fi

quote_toon() {
  printf '%s' "$1" | sed 's/\\/\\\\/g; s/"/\\"/g'
}

field() {
  printf '%s: "%s"\n' "$1" "$(quote_toon "$2")"
}

usage() {
  if [ "$presentation" = claude ]; then
    field description 'Install Braintree for Claude Code into an explicit project or home-root directory.'
    field usage 'scripts/install-claude.sh (--project DIR | --home DIR) [--dry-run]'
    printf 'options[6]{flag,meaning}:\n'
    printf '  "--project DIR","install to DIR/.claude/skills/braintree"\n'
    printf '  "--home DIR","use an explicit home root; never defaults to $HOME"\n'
    printf '  "--dry-run","report the destination without writing"\n'
    printf '  "--help, -h","show this reference"\n'
    printf '  "--version","print the version only when passed alone"\n'
    printf '  "-v, -V","aliases for bare --version"\n'
    printf 'examples[3]{command,purpose}:\n'
    printf '  "./scripts/install-claude.sh --project /path/to/project --dry-run","inspect a Claude Code project destination"\n'
    printf '  "./scripts/install-claude.sh --project /path/to/project","install for a Claude Code project"\n'
    printf '  "./scripts/install-claude.sh --home $HOME","install for Claude Code only with an explicit home root"\n'
    return
  fi

  field description 'Install Braintree into an explicit project or home-root directory.'
  field usage 'scripts/install.sh (--codex | --claude | --pi) (--project DIR | --home DIR) [--dry-run]'
  field claude_wrapper 'scripts/install-claude.sh omits --claude and accepts the same destination flags.'
  printf 'options[9]{flag,meaning}:\n'
  printf '  "--codex","install to DIR/.agents/skills/braintree"\n'
  printf '  "--claude","install to DIR/.claude/skills/braintree"\n'
  printf '  "--pi","install to DIR/.pi/skills/braintree (project) or DIR/.pi/agent/skills/braintree (home)"\n'
  printf '  "--project DIR","use an explicit project directory"\n'
  printf '  "--home DIR","use an explicit home root; never defaults to $HOME"\n'
  printf '  "--dry-run","report the destination without writing"\n'
  printf '  "--help, -h","show this reference"\n'
  printf '  "--version","print the version only when passed alone"\n'
  printf '  "-v, -V","aliases for bare --version"\n'
  printf 'examples[4]{command,purpose}:\n'
  printf '  "./scripts/install.sh --codex --project /path/to/project --dry-run","inspect a Codex project destination"\n'
  printf '  "./scripts/install.sh --claude --project /path/to/project","install for a Claude Code project"\n'
  printf '  "./scripts/install.sh --pi --project /path/to/project","install for a pi project"\n'
  printf '  "./scripts/install.sh --codex --home $HOME","install for Codex only with an explicit home root"\n'
}

usage_error() {
  field error "$1"
  if [ "$presentation" = claude ]; then
    field help 'scripts/install-claude.sh --project <directory> [--dry-run]'
  else
    field help 'scripts/install.sh --codex --project <directory> [--dry-run]'
  fi
  exit 2
}

runtime_error() {
  field error "$1"
  field help 'Check the explicit destination directory and its permissions, then retry.'
  exit 1
}

while [ "$#" -gt 0 ]; do
  case "$1" in
    --codex|--claude|--pi)
      [ -z "$agent" ] || usage_error 'select exactly one agent: --codex, --claude, or --pi'
      agent=${1#--}
      ;;
    --project|--home)
      [ -z "$scope" ] || usage_error 'select exactly one destination scope: --project or --home'
      scope=${1#--}
      shift
      [ "$#" -gt 0 ] || usage_error "--$scope requires a directory"
      root=$1
      ;;
    --dry-run) dry_run=true ;;
    --help|-h) usage; exit 0 ;;
    *) usage_error "unknown argument: $1" ;;
  esac
  shift
done

[ -n "$agent" ] && [ -n "$scope" ] || usage_error 'agent and destination scope are required'
[ -d "$root" ] || runtime_error "directory does not exist: $root"

case "$agent" in
  codex) destination="$root/.agents/skills/$skill_name" ;;
  claude) destination="$root/.claude/skills/$skill_name" ;;
  pi)
    # pi discovers project skills under .pi/skills and global skills under
    # ~/.pi/agent/skills, so the relative path depends on the destination scope.
    case "$scope" in
      home) destination="$root/.pi/agent/skills/$skill_name" ;;
      *) destination="$root/.pi/skills/$skill_name" ;;
    esac
    ;;
esac

if [ "$dry_run" = true ]; then
  field result dry-run
  field agent "$agent"
  field destination "$destination"
  exit 0
fi

changed=false

# Install one repository file into the skill destination, preserving its
# relative path. The skill is a `uv` project: installed copies are invoked as
# `uv run --project <destination> --frozen bt ...` and `... graph-check ...`.
copy_file() {
  relative=$1
  mode=$2
  source="$repo_root/$relative"
  target="$destination/$relative"
  if [ -f "$target" ] && cmp -s "$source" "$target"; then
    return
  fi
  mkdir -p "$(dirname -- "$target")" 2>/dev/null || runtime_error "unable to create directory for: $target"
  install -m "$mode" "$source" "$target" 2>/dev/null || runtime_error "unable to install: $target"
  changed=true
}

copy_file SKILL.md 0644
if [ "$agent" = codex ]; then
  copy_file agents/openai.yaml 0644
fi
for metadata in pyproject.toml uv.lock .python-version README.md; do
  copy_file "$metadata" 0644
done
for source in "$repo_root"/src/braintree/*; do
  [ -f "$source" ] || continue
  copy_file "src/braintree/$(basename -- "$source")" 0644
done

if [ "$changed" = true ]; then
  field result installed
else
  field result no-op
fi
field agent "$agent"
field destination "$destination"
