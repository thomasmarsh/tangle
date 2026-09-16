#!/bin/sh
# Install this skill into an explicitly selected Codex, Claude Code, or pi
# location, and install the ``tangle`` command that fronts it.
set -eu

# The project version is declared once in ``pyproject.toml``. Read it here so
# the installer and the installed package always report the same number.
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd) || exit 1
version=$(sed -n 's/^version *= *"\([^"]*\)".*/\1/p' "$repo_root/pyproject.toml" | head -n 1)
if [ -z "$version" ]; then
  printf '%s\n' 'error: "unable to read the project version from pyproject.toml"'
  exit 1
fi

skill_name=tangle
agent=
scope=
root=
dry_run=false
semantic=false
selector=false
presentation=${TANGLE_INSTALL_PRESENTATION:-generic}

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
    field description 'Install Tangle for Claude Code into an explicit project or home-root directory.'
    field usage 'scripts/install-claude.sh [--project DIR | --home DIR] [--dry-run] [--semantic]'
    field default 'With no destination flag, installs the shared command and the Claude Code skill into $HOME.'
    field launcher 'DIR/.local/bin/tangle, the single documented entry point'
    field program 'DIR/.local/share/tangle, the one shared program per root the launcher runs'
    printf 'options[7]{flag,meaning}:\n'
    printf '  "--project DIR","install to DIR/.claude/skills/tangle"\n'
    printf '  "--home DIR","use an explicit home root; defaults to $HOME when omitted"\n'
    printf '  "--dry-run","report the destination without writing"\n'
    printf '  "--semantic","request the optional semantic extra in the generated launcher"\n'
    printf '  "--help, -h","show this reference"\n'
    printf '  "--version","print the version only when passed alone"\n'
    printf '  "-v, -V","aliases for bare --version"\n'
    printf 'examples[4]{command,purpose}:\n'
    printf '  "./scripts/install-claude.sh","install the shared command and the Claude Code skill into $HOME"\n'
    printf '  "./scripts/install-claude.sh --project /path/to/project","install for a Claude Code project"\n'
    printf '  "./scripts/install-claude.sh --home $HOME --semantic","install with the optional semantic extra"\n'
    printf '  "./scripts/install-claude.sh --project /path/to/project --dry-run","inspect a Claude Code project destination"\n'
    return
  fi

  field description 'Install Tangle into an explicit project or home-root directory, or select targets interactively.'
  field usage 'scripts/install.sh [--codex | --claude | --pi] [--project DIR | --home DIR] [--dry-run] [--semantic] [--select]'
  field default 'With no flags, installs the shared command and every agent skill into $HOME; pass --select to choose other targets.'
  field interactive 'With --select, discovers the enclosing project root and the home root and multi-selects their agent targets; a bare --select needs a terminal or TANGLE_INSTALL_SELECTION.'
  field claude_wrapper 'scripts/install-claude.sh omits --claude and accepts the same destination flags.'
  field launcher 'DIR/.local/bin/tangle, the single documented entry point'
  field program 'DIR/.local/share/tangle, the one shared program per root the launcher runs'
  printf 'options[11]{flag,meaning}:\n'
  printf '  "--codex","install to DIR/.agents/skills/tangle"\n'
  printf '  "--claude","install to DIR/.claude/skills/tangle"\n'
  printf '  "--pi","install to DIR/.pi/skills/tangle (project) or DIR/.pi/agent/skills/tangle (home)"\n'
  printf '  "--project DIR","use an explicit project directory"\n'
  printf '  "--home DIR","use an explicit home root; defaults to $HOME when the scope is omitted"\n'
  printf '  "--select","choose discovered targets interactively instead of the defaults"\n'
  printf '  "--dry-run","report the destination without writing"\n'
  printf '  "--semantic","request the optional semantic extra in the generated launcher"\n'
  printf '  "--help, -h","show this reference"\n'
  printf '  "--version","print the version only when passed alone"\n'
  printf '  "-v, -V","aliases for bare --version"\n'
  printf 'examples[6]{command,purpose}:\n'
  printf '  "./scripts/install.sh","install the shared command and every agent skill into $HOME"\n'
  printf '  "./scripts/install.sh --pi","install pi at $HOME"\n'
  printf '  "./scripts/install.sh --select","choose discovered targets interactively"\n'
  printf '  "./scripts/install.sh --codex --project /path/to/project --dry-run","inspect a Codex project destination"\n'
  printf '  "./scripts/install.sh --pi --project /path/to/project","install for a pi project"\n'
  printf '  "./scripts/install.sh --pi --home $HOME --semantic","install with the optional semantic extra"\n'
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

# Resolve the agent destination for a destination scope and root. Codex and
# Claude Code have one location each; pi discovers project skills under
# ``.pi/skills`` and global skills under ``.pi/agent/skills``, so its relative
# path depends on the scope.
destination_for() {
  case "$1" in
    codex) printf '%s\n' "$3/.agents/skills/$skill_name" ;;
    claude) printf '%s\n' "$3/.claude/skills/$skill_name" ;;
    pi)
      case "$2" in
        home) printf '%s\n' "$3/.pi/agent/skills/$skill_name" ;;
        *) printf '%s\n' "$3/.pi/skills/$skill_name" ;;
      esac
      ;;
  esac
}

# The nearest enclosing directory that carries a real project marker. The walk
# never guesses a directory and never escapes the filesystem root.
discover_project_root() {
  discovered_dir=$PWD
  while :; do
    for discovered_marker in .git pyproject.toml package.json Cargo.toml go.mod; do
      if [ -e "$discovered_dir/$discovered_marker" ]; then
        printf '%s\n' "$discovered_dir"
        return 0
      fi
    done
    discovered_parent=$(dirname -- "$discovered_dir")
    [ "$discovered_parent" != "$discovered_dir" ] || return 1
    discovered_dir=$discovered_parent
  done
}

# Install one repository file into a base directory, preserving its relative
# path. The agent destination receives only the skill prose it discovers; the
# program the generated ``tangle`` command runs goes to the shared location.
copy_file() {
  base=$1
  relative=$2
  mode=$3
  source="$repo_root/$relative"
  target="$base/$relative"
  if [ -f "$target" ] && cmp -s "$source" "$target"; then
    return
  fi
  mkdir -p "$(dirname -- "$target")" 2>/dev/null || runtime_error "unable to create directory for: $target"
  install -m "$mode" "$source" "$target" 2>/dev/null || runtime_error "unable to install: $target"
  changed=true
}

# Install one resolved target: the skill prose at its agent destination, the one
# shared program per root with its install record, and the single launcher. It
# prints nothing and reports through ``outcome``, ``destination``,
# ``program_dir``, and ``launcher``, so the explicit and the interactive paths
# report the same fields.
install_target() {
  target_agent=$1
  target_scope=$2
  target_root=$3
  [ -d "$target_root" ] || runtime_error "directory does not exist: $target_root"
  destination=$(destination_for "$target_agent" "$target_scope" "$target_root")

  # One shared program per root, independent of which agent discovers the skill.
  # Every agent's generated command runs this copy, so an agent install cannot
  # repoint it at another agent's files.
  program_dir="$target_root/.local/share/$skill_name"

  # The launcher the installer writes below fronts the one shared per-root
  # program, so its target is fixed here once per target.
  launcher_dir="$target_root/.local/bin"
  launcher="$launcher_dir/tangle"

  if [ "$dry_run" = true ]; then
    outcome=dry-run
    return 0
  fi
  changed=false

  # The agent destination is only the skill prose the agent discovers: the core,
  # the canonical reference tree it renders, and agent metadata. It never carries
  # the program, so installing an agent cannot repoint or rebuild the command.
  copy_file "$destination" SKILL.md 0644
  for reference in "$repo_root"/references/*.md; do
    [ -f "$reference" ] || continue
    copy_file "$destination" "references/$(basename -- "$reference")" 0644
  done
  if [ "$target_agent" = codex ]; then
    copy_file "$destination" agents/openai.yaml 0644
  fi

  # The program is installed once per root. Copy a file only when it is missing or
  # differs, so reinstalling another agent leaves this revision untouched. When
  # the program drifts from this checkout, the differing bytes and the record
  # below refresh it; the released version and the exact copied bytes are the
  # compatibility check.
  for metadata in pyproject.toml uv.lock .python-version README.md; do
    copy_file "$program_dir" "$metadata" 0644
  done
  for reference in "$repo_root"/references/*.md; do
    [ -f "$reference" ] || continue
    copy_file "$program_dir" "references/$(basename -- "$reference")" 0644
  done
  for source in "$repo_root"/src/tangle/*; do
    [ -f "$source" ] || continue
    copy_file "$program_dir" "src/tangle/$(basename -- "$source")" 0644
  done

  # Removed research implementations must not survive an in-place upgrade from
  # an older release. This is intentionally an explicit retired path rather than
  # a broad directory reconciliation: the installer owns no unlisted user files.
  retired_behavioral="$program_dir/src/tangle/behavioral_benchmark.py"
  if [ -e "$retired_behavioral" ]; then
    rm -f -- "$retired_behavioral" 2>/dev/null \
      || runtime_error "unable to remove retired research module: $retired_behavioral"
    changed=true
  fi

  # Record the release version and the source revision the shared program was
  # copied from as generated install data. The installed ``tangle`` command
  # reads it back with `--version`, so a consuming project can name the exact
  # revision in use without network access or the original checkout. The value
  # matches the ``tangle_revision`` convention: ``<version>+g<short-sha>`` when
  # a source revision is available, else ``<version>+unknown``. The semantic
  # version is still declared once in pyproject.toml; this record only stamps it.
  source_revision=unknown
  if command -v git >/dev/null 2>&1; then
    detected=$(git -C "$repo_root" rev-parse --short=7 HEAD 2>/dev/null || true)
    case "$detected" in
      [0-9a-f][0-9a-f]*) source_revision="g$detected" ;;
    esac
  fi
  record_value="$version+$source_revision"
  record="$program_dir/src/tangle/installed-revision"
  if [ ! -f "$record" ] || [ "$(cat "$record")" != "$record_value" ]; then
    mkdir -p "$(dirname -- "$record")" 2>/dev/null || runtime_error "unable to create directory for: $record"
    printf '%s\n' "$record_value" >"$record" 2>/dev/null || runtime_error "unable to install: $record"
    chmod 0644 "$record" 2>/dev/null || runtime_error "unable to install: $record"
    changed=true
  fi

  # Install the single language-agnostic command that fronts the skill. It
  # points at the one shared per-root program, never at an agent destination, so
  # reinstalling any agent cannot repoint it. A consumer runs ``tangle`` from
  # any project root without naming the toolchain or layout. Only an explicit
  # --semantic install requests the optional extra, so a plain install keeps the
  # launcher on the dependency-free frozen set. The parameter expansions insert
  # the flag and the provider default without changing the plain launcher bytes,
  # and an operator-set provider always wins.
  launcher_extra=
  launcher_provider=
  if [ "$semantic" = true ]; then
    launcher_extra="--extra semantic"
    launcher_provider='if [ -z "${TANGLE_SEMANTIC_PROVIDER+set}" ]; then
  TANGLE_SEMANTIC_PROVIDER="tangle semantic embed"
  export TANGLE_SEMANTIC_PROVIDER
fi
'
  fi
  # Materialize the shared program's environment once, at install time, so the
  # generated launcher can run it directly. A read-only command must not need a
  # writable uv cache: sandboxes commonly deny the user-home cache, and uv run
  # initializes it before dispatching. The launcher still falls back to uv run
  # when this environment is absent.
  uv sync --project "$program_dir" --frozen ${launcher_extra} >/dev/null 2>&1 \
    || runtime_error "unable to prepare the program environment: $program_dir"

  launcher_body=$(cat <<EOF
#!/bin/sh
# Generated by the Tangle installer: run the shared per-root program.
set -eu
${launcher_provider}if [ -x "$program_dir/.venv/bin/tangle" ]; then
  exec "$program_dir/.venv/bin/tangle" "\$@"
fi
exec uv run --project "$program_dir" --frozen ${launcher_extra:+$launcher_extra }tangle "\$@"
EOF
)
  if [ ! -f "$launcher" ] || [ "$(cat "$launcher")" != "$launcher_body" ]; then
    mkdir -p "$launcher_dir" 2>/dev/null || runtime_error "unable to create directory for: $launcher"
    printf '%s\n' "$launcher_body" >"$launcher" 2>/dev/null || runtime_error "unable to install: $launcher"
    chmod 0755 "$launcher" 2>/dev/null || runtime_error "unable to install: $launcher"
    changed=true
  fi

  if [ "$changed" = true ]; then
    outcome=installed
  else
    outcome=no-op
  fi
}

# Zero-config install: install the shared command and every supported agent at
# one root. The shared program and launcher are written once per root, so the
# first agent may report ``installed`` while the rest report ``no-op``; the
# aggregate result is ``installed`` when any target changed. Rows use the same
# shape as the interactive selector, so one parser reads both.
install_group() {
  group_scope=$1
  group_root=$2
  [ -d "$group_root" ] || runtime_error "directory does not exist: $group_root"
  group_changed=false
  group_rows=
  group_count=0
  for group_agent in codex claude pi; do
    install_target "$group_agent" "$group_scope" "$group_root"
    group_count=$((group_count+1))
    if [ "$outcome" = installed ]; then
      group_changed=true
    fi
    group_rows="${group_rows}  \"${group_agent}\",\"${destination}\",\"${program_dir}\",\"${launcher}\",\"${outcome}\"
"
  done
  if [ "$dry_run" = true ]; then
    group_result=dry-run
  elif [ "$group_changed" = true ]; then
    group_result=installed
  else
    group_result=no-op
  fi
  field result "$group_result"
  field selected "$group_count"
  field scope "$group_scope"
  field root "$group_root"
  field program "$program_dir"
  if [ "$dry_run" != true ]; then
    field launcher "$launcher"
  fi
  printf 'outcomes[%s]{agent,destination,program,launcher,result}:\n' "$group_count"
  printf '%s' "$group_rows"
  if [ "$semantic" = true ] && [ "$dry_run" != true ]; then
    field provider "defaults to tangle semantic embed; override with TANGLE_SEMANTIC_PROVIDER"
  fi
}

# Interactive selector: discover candidate roots, cross them with the
# supported agents, present a numbered multi-select, and install every selected
# target. A non-terminal stdin never prompts, so an automated run stays
# deterministic instead of hanging. ``TANGLE_INSTALL_SELECTION`` supplies the
# selection directly, which exercises the selector without a terminal.
interactive_select() {
  if [ -z "${TANGLE_INSTALL_SELECTION+set}" ] && [ ! -t 0 ]; then
    field error 'no install target: a bare --select needs a terminal; pass --codex, --claude, or --pi with --project DIR or --home DIR'
    field help 'scripts/install.sh --codex --project <directory> [--dry-run]'
    exit 2
  fi

  project_root=$(discover_project_root || true)
  home_root=
  if [ -n "${HOME-}" ] && [ -d "$HOME" ]; then
    home_root=$HOME
  fi
  # Present a root once when the home root is also the enclosing project root.
  if [ -n "$project_root" ] && [ "$project_root" = "$home_root" ]; then
    home_root=
  fi

  candidate_count=0
  candidates=
  for candidate_root in "$project_root" "$home_root"; do
    [ -n "$candidate_root" ] || continue
    if [ "$candidate_root" = "$project_root" ]; then
      candidate_scope=project
    else
      candidate_scope=home
    fi
    for candidate_agent in codex claude pi; do
      candidate_count=$((candidate_count+1))
      candidate_destination=$(destination_for "$candidate_agent" "$candidate_scope" "$candidate_root")
      candidates="${candidates}${candidate_count}	${candidate_agent}	${candidate_scope}	${candidate_root}	${candidate_destination}
"
    done
  done

  if [ "$candidate_count" -eq 0 ]; then
    field error 'no install target was discovered: pass --codex, --claude, or --pi with --project DIR or --home DIR'
    field help 'scripts/install.sh --codex --project <directory> [--dry-run]'
    exit 2
  fi

  field result menu
  printf 'targets[%s]{index,agent,root,destination}:\n' "$candidate_count"
  while IFS='	' read -r menu_index menu_agent menu_scope menu_root menu_destination; do
    [ -n "$menu_index" ] || continue
    printf '  "%s","%s","%s","%s"\n' "$menu_index" "$menu_agent" "$menu_root" "$menu_destination"
  done <<CANDIDATES
$candidates
CANDIDATES
  field prompt 'Select install targets by number (space or comma separated, or "all"); empty cancels'

  if [ -n "${TANGLE_INSTALL_SELECTION+set}" ]; then
    selection=$TANGLE_INSTALL_SELECTION
  else
    IFS= read -r selection || selection=
  fi
  selection=$(printf '%s' "$selection" | tr ',' ' ')
  if [ "$selection" = all ]; then
    selection=
    candidate_index=1
    while [ "$candidate_index" -le "$candidate_count" ]; do
      selection="$selection $candidate_index"
      candidate_index=$((candidate_index+1))
    done
  fi

  chosen=
  chosen_count=0
  set -f
  for chosen_token in $selection; do
    case "$chosen_token" in
      *[!0-9]*)
        field error "invalid selection: $chosen_token"
        field help 'select the target numbers shown, space or comma separated, or all'
        exit 2
        ;;
    esac
    if [ "$chosen_token" -lt 1 ] || [ "$chosen_token" -gt "$candidate_count" ]; then
      field error "selection out of range: $chosen_token"
      field help "choose a number from 1 to $candidate_count"
      exit 2
    fi
    case " $chosen " in
      *" $chosen_token "*) continue ;;
    esac
    chosen="$chosen $chosen_token"
    chosen_count=$((chosen_count+1))
  done
  set +f
  chosen=${chosen# }

  if [ "$chosen_count" -eq 0 ]; then
    field result cancelled
    return 0
  fi

  field result multi
  field selected "$chosen_count"
  printf 'outcomes[%s]{agent,destination,program,launcher,result}:\n' "$chosen_count"
  while IFS='	' read -r menu_index menu_agent menu_scope menu_root menu_destination; do
    [ -n "$menu_index" ] || continue
    case " $chosen " in
      *" $menu_index "*) ;;
      *) continue ;;
    esac
    install_target "$menu_agent" "$menu_scope" "$menu_root"
    printf '  "%s","%s","%s","%s","%s"\n' "$menu_agent" "$destination" "$program_dir" "$launcher" "$outcome"
  done <<CANDIDATES
$candidates
CANDIDATES
  if [ "$semantic" = true ] && [ "$dry_run" != true ]; then
    field provider "defaults to tangle semantic embed; override with TANGLE_SEMANTIC_PROVIDER"
  fi
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
    --semantic) semantic=true ;;
    --select) selector=true ;;
    --help|-h) usage; exit 0 ;;
    *) usage_error "unknown argument: $1" ;;
  esac
  shift
done

# A bare invocation installs the zero-config defaults; --select opts into the
# interactive selector, and the explicit flags stay the non-interactive
# contract. An omitted destination scope is the home root, so the shared command
# lands on PATH; an omitted agent installs every supported agent.
if [ "$selector" = true ]; then
  if [ -n "$agent" ] || [ -n "$scope" ]; then
    usage_error '--select cannot be combined with an agent or destination'
  fi
  interactive_select
  exit 0
fi

if [ -z "$scope" ]; then
  scope=home
  root=${HOME-}
  if [ -z "$root" ]; then
    usage_error 'no home root: set HOME or pass --project DIR'
  fi
fi

if [ -n "$agent" ]; then
  install_target "$agent" "$scope" "$root"
  field result "$outcome"
  field agent "$agent"
  field destination "$destination"
  field program "$program_dir"
  if [ "$dry_run" != true ]; then
    field launcher "$launcher"
    if [ "$semantic" = true ]; then
      field provider "defaults to tangle semantic embed; override with TANGLE_SEMANTIC_PROVIDER"
    fi
  fi
else
  install_group "$scope" "$root"
fi
