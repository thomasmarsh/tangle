#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM
nodes="$test_root/nodes"
mkdir -p "$nodes/active" "$nodes/resolved" "$nodes/blocked"

write_node() {
  path=$1
  shift
  printf '%s\n' "$@" >"$path"
}

write_node "$nodes/index-map.md" '---' 'updated: 2026-09-10T00:00:00Z' 'summary: Route graph work.' '---' '' '# Root hubs' '' '- Indexes [[IDX-001-root]].'
write_node "$nodes/resolved/IDX-001-root.md" '---' 'context_rev: 1' 'updated: 2026-09-10T00:00:00Z' 'summary: Root hub.' '---'
write_node "$nodes/resolved/DEF-001-contract.md" '---' 'context_rev: 1' 'updated: 2026-09-10T00:00:00Z' 'summary: Contract.' '---' '' 'Area [[IDX-001-root]].'
write_node "$nodes/active/TAS-001-parent.md" '---' 'context_rev: 1' 'updated: 2026-09-10T00:00:00Z' 'summary: Parent.' 'next: Continue [[TAS-002-child]].' '---' '' 'Area [[IDX-001-root]].' '' 'Depends on [[DEF-001-contract]] at context_rev 1.'
write_node "$nodes/active/TAS-002-child.md" '---' 'context_rev: 1' 'updated: 2026-09-10T00:00:00Z' 'summary: Child.' 'next: Finish the check.' '---' '' 'Parent [[TAS-001-parent]].'

"$repo_root/scripts/graph-check" "$nodes" >/dev/null

# An empty-vault bootstrap needs a routed IDX root before its first actionable
# node; this fixture exercises the shipped checker against that minimum shape.
bootstrap="$test_root/bootstrap-nodes"
mkdir -p "$bootstrap/active" "$bootstrap/resolved"
write_node "$bootstrap/index-map.md" '---' 'updated: 2026-09-10T00:00:00Z' 'summary: Route graph work.' '---' '' '# Root hubs' '' '- Indexes [[IDX-001-root]].'
write_node "$bootstrap/resolved/IDX-001-root.md" '---' 'context_rev: 1' 'updated: 2026-09-10T00:00:00Z' 'summary: Root hub.' '---' '' '# Invariant' '' 'No Parent or Area route.'
write_node "$bootstrap/active/TAS-001-first-action.md" '---' 'context_rev: 1' 'updated: 2026-09-10T00:00:00Z' 'summary: First actionable node.' 'next: Perform the first action.' '---' '' 'Area [[IDX-001-root]].'
"$repo_root/scripts/graph-check" "$bootstrap" >/dev/null

expect_error() {
  label=$1
  expected=$2
  if "$repo_root/scripts/graph-check" "$nodes" >"$test_root/out" 2>"$test_root/err"; then
    echo "expected graph check failure: $label" >&2
    exit 1
  fi
  if ! grep -F "$expected" "$test_root/err" >/dev/null; then
    echo "missing $label error: $expected" >&2
    cat "$test_root/err" >&2
    exit 1
  fi
}

cp "$nodes/active/TAS-001-parent.md" "$nodes/blocked/TAS-001-copy.md"
expect_error duplicate 'duplicate node identity: TAS-001'
rm "$nodes/blocked/TAS-001-copy.md"

printf '%s\n' 'Related to [[TAS-999-missing]].' >>"$nodes/active/TAS-002-child.md"
expect_error broken-link 'broken link [[TAS-999-missing]]'
sed '$d' "$nodes/active/TAS-002-child.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-002-child.md"

sed '/^next:/d' "$nodes/active/TAS-002-child.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-002-child.md"
expect_error next 'unfinished task requires next'
awk '{ print; if ($0 == "summary: Child.") print "next: Finish the check." }' "$nodes/active/TAS-002-child.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-002-child.md"

sed 's/context_rev 1\./context_rev 2./' "$nodes/active/TAS-001-parent.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-001-parent.md"
expect_error revision 'context_rev mismatch'
sed 's/context_rev 2\./context_rev 1./' "$nodes/active/TAS-001-parent.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-001-parent.md"

sed 's/ at context_rev 1\././' "$nodes/active/TAS-001-parent.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-001-parent.md"
expect_error unpinned 'invalid or missing context_rev pin'
sed '/^Depends on /s/\]\]\./]] at context_rev 1./' "$nodes/active/TAS-001-parent.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-001-parent.md"

printf '%s\n' 'Child [[TAS-002-child]].' >>"$nodes/active/TAS-001-parent.md"
expect_error canonical-edge 'stored reciprocal edge'
sed '$d' "$nodes/active/TAS-001-parent.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-001-parent.md"

sed 's/Parent \[\[TAS-001-parent\]\]\./Parent [[TAS-777-missing]]./' "$nodes/active/TAS-002-child.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-002-child.md"
expect_error orphan 'orphan unfinished node'
sed 's/Parent \[\[TAS-777-missing\]\]\./Parent [[TAS-001-parent]]./' "$nodes/active/TAS-002-child.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-002-child.md"

sed 's/Parent \[\[TAS-001-parent\]\]\./Parent [[TAS-002-child]]./' "$nodes/active/TAS-002-child.md" >"$test_root/node" && mv "$test_root/node" "$nodes/active/TAS-002-child.md"
expect_error parent-cycle 'parent cycle'

printf 'graph checker tests: passed\n'
