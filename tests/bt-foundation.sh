#!/bin/sh
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM
export BT_SIDECAR_DIR="$test_root/sidecar" BT_PROJECT_ID=test-project BT_NODES_DIR="$test_root/vault/nodes"
bt="$repo_root/scripts/bt"
expected_version=$(sed -n 's/^version *= *"\([^"]*\)".*/\1/p' "$repo_root/pyproject.toml" | head -n 1)
[ "$("$bt" --version)" = "$expected_version" ]
case "$("$bt" status)" in *'initialized: "false"'*) ;; *) exit 1;; esac
"$bt" init | grep -F 'result: "initialized"' >/dev/null
[ -f "$BT_SIDECAR_DIR/projects/test-project/graph.sqlite3" ]
sqlite3 "$BT_SIDECAR_DIR/projects/test-project/graph.sqlite3" 'PRAGMA journal_mode;' | grep -Fx wal >/dev/null
[ "$("$bt" allocate TAS)" = 'id: "TAS-001"' ]; [ "$("$bt" allocate TAS)" = 'id: "TAS-002"' ]; [ "$("$bt" allocate DEF)" = 'id: "DEF-001"' ]
"$bt" claim TAS-001 agent-a --base-hash abc --lease-seconds 60 | grep -F 'result: "claimed"' >/dev/null
"$bt" claim TAS-001 agent-a --base-hash abc --lease-seconds 60 | grep -F 'result: "claimed"' >/dev/null
case "$("$bt" claim TAS-001 agent-b --base-hash abc 2>/dev/null || true)" in *'error: "node is claimed by agent-a with a different base hash"'*) ;; *) exit 1;; esac
case "$("$bt" claim TAS-001 agent-a --base-hash def 2>/dev/null || true)" in *'error: "node is claimed by agent-a with a different base hash"'*) ;; *) exit 1;; esac
"$bt" release TAS-001 agent-a --base-hash abc | grep -F 'result: "released"' >/dev/null
"$bt" release TAS-001 agent-a --base-hash abc | grep -F 'result: "no-op"' >/dev/null
"$bt" claim TAS-001 agent-b --base-hash def --lease-seconds 1 >/dev/null; sleep 1
"$bt" claim TAS-001 agent-a --base-hash ghi --lease-seconds 60 | grep -F 'result: "claimed"' >/dev/null
case "$("$bt" claim TAS-002 agent-a --bogus x 2>/dev/null || true)" in *'error: "unknown argument for claim: --bogus"'*) ;; *) exit 1;; esac
printf 'bt foundation tests: passed\n'
