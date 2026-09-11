#!/bin/sh
# Disposable correctness screen for the external bt coordination sidecar.
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM
bt="$repo_root/scripts/bt"
sidecar="$test_root/sidecar"
export BT_SIDECAR_DIR="$sidecar" BT_PROJECT_ID=verification-test
db="$sidecar/projects/verification-test/graph.sqlite3"
fail() { printf '%s\n' "bt verification: $*" >&2; exit 1; }

# BEGIN IMMEDIATE must provide one owner and non-overlapping IDs under contention.
"$bt" init >/dev/null
"$bt" claim TAS-900 agent-a --base-hash hash-a --lease-seconds 60 >"$test_root/claim-a" 2>&1 & claim_a=$!
"$bt" claim TAS-900 agent-b --base-hash hash-b --lease-seconds 60 >"$test_root/claim-b" 2>&1 & claim_b=$!
wait "$claim_a" || true
wait "$claim_b" || true
claimed=$(grep -l 'result: "claimed"' "$test_root/claim-a" "$test_root/claim-b" | wc -l | tr -d ' ')
[ "$claimed" = 1 ] || fail 'claim contention did not produce exactly one owner'

pids=
for n in 1 2 3 4 5 6 7 8; do "$bt" allocate CON >"$test_root/allocate-$n" 2>&1 & pids="$pids $!"; done
for pid in $pids; do wait "$pid" || fail 'concurrent allocation failed'; done
ids=$(sed -n 's/^id: "\(.*\)"$/\1/p' "$test_root"/allocate-* | sort)
[ "$(printf '%s\n' "$ids" | uniq | wc -l | tr -d ' ')" = 8 ] || fail 'concurrent allocation duplicated an ID'
[ "$(printf '%s\n' "$ids" | paste -sd ' ' -)" = 'CON-001 CON-002 CON-003 CON-004 CON-005 CON-006 CON-007 CON-008' ] || fail 'concurrent allocation skipped an ID'

# Expiration is controlled directly rather than relying on a timing sleep.
"$bt" claim TAS-901 agent-a --base-hash old --lease-seconds 60 >/dev/null
sqlite3 "$db" "UPDATE claims SET lease_expires_at=0 WHERE node_id='TAS-901';"
"$bt" claim TAS-901 agent-b --base-hash new --lease-seconds 60 | grep -F 'agent: "agent-b"' >/dev/null
case "$("$bt" claim TAS-901 agent-b --base-hash changed --lease-seconds 60 2>/dev/null || true)" in *'different base hash'*) ;; *) fail 'base-hash mismatch was accepted';; esac

vault="$test_root/vault/nodes"
mkdir -p "$vault/resolved" "$vault/active"
printf '%s\n' \
  '---' 'context_rev: 1' 'updated: 2026-09-11T00:00:00Z' 'summary: Root.' '---' '' '# Invariant' '' 'Root.' >"$vault/resolved/IDX-001-root.md"
printf '%s\n' \
  '---' 'context_rev: 2' 'updated: 2026-09-11T00:00:00Z' 'summary: Durable definition.' '---' '' '# Context' '' 'Area [[IDX-001-root]].' '' '# Invariant' '' 'Search needle.' >"$vault/resolved/DEF-001-definition.md"
printf '%s\n' \
  '---' 'context_rev: 1' 'updated: 2026-09-11T00:00:00Z' 'summary: Consumer.' 'next: Reconcile.' '---' '' '# Context' '' 'Parent [[IDX-001-root]].' '' 'Depends on [[DEF-001-definition]] at context_rev 1.' >"$vault/active/TAS-001-consumer.md"
before=$(find "$vault" -type f -print0 | sort -z | xargs -0 shasum)
"$bt" reindex "$vault" >/dev/null
export BT_NODES_DIR="$vault"
"$bt" search needle | grep -F '"DEF-001","resolved"' >/dev/null
"$bt" backlinks DEF-001 | grep -F '"TAS-001","active","Depends on","1"' >/dev/null
"$bt" stale | grep -F '"TAS-001","active","DEF-001","1","2"' >/dev/null
after=$(find "$vault" -type f -print0 | sort -z | xargs -0 shasum)
[ "$before" = "$after" ] || fail 'sidecar commands modified authoritative Markdown'
rm -f "$db"
"$bt" reindex "$vault" >/dev/null
"$bt" search needle | grep -F '"DEF-001","resolved"' >/dev/null
unset BT_NODES_DIR

# Stable Git-common-dir identity makes claims visible across local worktrees.
repo="$test_root/repo" tree_a="$test_root/tree-a" tree_b="$test_root/tree-b"
git init -q -b main "$repo"
git -C "$repo" config user.email bt-test@example.invalid
git -C "$repo" config user.name 'BT Test'
printf 'fixture\n' >"$repo/README.md"
git -C "$repo" add README.md && git -C "$repo" commit -qm fixture
git -C "$repo" worktree add -q -b tree-a "$tree_a" main
git -C "$repo" worktree add -q -b tree-b "$tree_b" main
unset BT_PROJECT_ID
id_a=$(cd "$tree_a" && "$bt" location | sed -n 's/^project_id: "\(.*\)"$/\1/p')
id_b=$(cd "$tree_b" && "$bt" location | sed -n 's/^project_id: "\(.*\)"$/\1/p')
[ -n "$id_a" ] && [ "$id_a" = "$id_b" ] || fail 'worktrees did not share project identity'
(cd "$tree_a" && "$bt" claim TAS-902 tree-a --base-hash base --lease-seconds 60 >/dev/null)
case "$(cd "$tree_b" && "$bt" claim TAS-902 tree-b --base-hash base --lease-seconds 60 2>/dev/null || true)" in *'claimed by tree-a'*) ;; *) fail 'worktrees did not share claim state';; esac

# A mocked df response proves the local-filesystem guard without network access.
mock_bin="$test_root/mock-bin"; mkdir "$mock_bin"
printf '%s\n' '#!/bin/sh' 'printf "%s\\n" "Filesystem 1024-blocks Used Available Capacity Mounted on" "server:/bt 1 1 0 100%% /mock"' >"$mock_bin/df"
chmod +x "$mock_bin/df"
export BT_PROJECT_ID=network-guard BT_SIDECAR_DIR="$test_root/network-sidecar"
case "$(PATH="$mock_bin:$PATH" "$bt" init 2>/dev/null || true)" in *'filesystem appears network-mounted'*) ;; *) fail 'network filesystem guard did not refuse sidecar';; esac

printf '%s\n' 'bt verification tests: passed'
