#!/bin/sh
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM
export KG_SIDECAR_DIR="$test_root/sidecar" KG_PROJECT_ID=test-project
kg="$repo_root/scripts/kg"
[ "$("$kg" --version)" = 0.1.0 ]
case "$("$kg" status)" in *'initialized: "false"'*) ;; *) exit 1;; esac
"$kg" init | grep -F 'result: "initialized"' >/dev/null
[ -f "$KG_SIDECAR_DIR/projects/test-project/graph.sqlite3" ]
sqlite3 "$KG_SIDECAR_DIR/projects/test-project/graph.sqlite3" 'PRAGMA journal_mode;' | grep -Fx wal >/dev/null
[ "$("$kg" allocate TAS)" = 'id: "TAS-001"' ]; [ "$("$kg" allocate TAS)" = 'id: "TAS-002"' ]; [ "$("$kg" allocate DEF)" = 'id: "DEF-001"' ]
"$kg" claim TAS-001 agent-a --base-hash abc --lease-seconds 60 | grep -F 'result: "claimed"' >/dev/null
"$kg" claim TAS-001 agent-a --base-hash abc --lease-seconds 60 | grep -F 'result: "claimed"' >/dev/null
case "$("$kg" claim TAS-001 agent-b --base-hash abc 2>/dev/null || true)" in *'error: "node is claimed by agent-a with a different base hash"'*) ;; *) exit 1;; esac
case "$("$kg" claim TAS-001 agent-a --base-hash def 2>/dev/null || true)" in *'error: "node is claimed by agent-a with a different base hash"'*) ;; *) exit 1;; esac
"$kg" release TAS-001 agent-a --base-hash abc | grep -F 'result: "released"' >/dev/null
"$kg" release TAS-001 agent-a --base-hash abc | grep -F 'result: "no-op"' >/dev/null
"$kg" claim TAS-001 agent-b --base-hash def --lease-seconds 1 >/dev/null; sleep 1
"$kg" claim TAS-001 agent-a --base-hash ghi --lease-seconds 60 | grep -F 'result: "claimed"' >/dev/null
case "$("$kg" claim TAS-002 agent-a --bogus x 2>/dev/null || true)" in *'error: "unknown argument for claim: --bogus"'*) ;; *) exit 1;; esac
printf 'kg foundation tests: passed\n'
