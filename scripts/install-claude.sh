#!/bin/sh
# Install this skill for Claude Code without requiring the generic --claude flag.
set -eu

repo_root=$(CDPATH= cd "$(dirname "$0")/.." && pwd)

# Preserve the generic installer's bare version fast path. All other parsing
# and installation behavior stays in scripts/install.sh; its presentation mode
# keeps wrapper help and usage errors executable without hidden arguments.
if [ "$#" -eq 1 ]; then
  case "$1" in
    --version|-v|-V) exec "$repo_root/scripts/install.sh" "$1" ;;
  esac
fi

BT_INSTALL_PRESENTATION=claude exec "$repo_root/scripts/install.sh" --claude "$@"
