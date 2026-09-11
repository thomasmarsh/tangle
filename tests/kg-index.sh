#!/bin/sh
set -eu
repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
test_root=$(mktemp -d)
trap 'rm -rf "$test_root"' EXIT HUP INT TERM
vault="$test_root/vault/nodes"
mkdir -p "$vault/resolved" "$vault/active"
cat > "$vault/resolved/IDX-001-root.md" <<'EOF'
---
context_rev: 2
updated: 2026-09-11T00:00:00Z
summary: Root graph entry.
---

# Invariant

Root content finds all work.
EOF
cat > "$vault/resolved/DEF-001-contract.md" <<'EOF'
---
context_rev: 3
updated: 2026-09-11T00:00:00Z
summary: Searchable protocol contract.
---

# Context

Area [[IDX-001-root]].

# Invariant

The protocol uses a durable token.
EOF
cat > "$vault/active/TAS-001-consumer.md" <<'EOF'
---
context_rev: 1
priority: P1
updated: 2026-09-11T00:00:00Z
summary: Consume the protocol.
next: Reconcile the contract.
---

# Context

Parent [[IDX-001-root]].

Depends on [[DEF-001-contract]] at context_rev 2.

# Outcome

Use the durable token.
EOF
cat > "$vault/active/TAS-002-missing.md" <<'EOF'
---
context_rev: 1
updated: 2026-09-11T00:00:00Z
summary: Recover a missing dependency.
next: Locate it.
---

# Context

Parent [[IDX-001-root]].

Depends on [[DEF-404-missing]].
EOF
export KG_SIDECAR_DIR="$test_root/sidecar" KG_PROJECT_ID=index-test KG_NODES_DIR="$vault"
kg="$repo_root/scripts/kg"
output=$("$kg" reindex)
printf '%s\n' "$output" | grep -Fx 'nodes: 4' >/dev/null
printf '%s\n' "$output" | grep -Fx 'edges: 5' >/dev/null
"$kg" search durable | grep -F '"DEF-001","resolved","Searchable protocol contract."' >/dev/null
"$kg" backlinks DEF-001 | grep -F '"TAS-001","active","Depends on","2"' >/dev/null
stale=$("$kg" stale)
printf '%s\n' "$stale" | grep -F '"TAS-001","active","DEF-001","2","3"' >/dev/null
printf '%s\n' "$stale" | grep -F '"TAS-002","active","DEF-404-missing","",""' >/dev/null
rm -f "$KG_SIDECAR_DIR/projects/index-test/graph.sqlite3"
"$kg" reindex >/dev/null
"$kg" search protocol | grep -F '"DEF-001"' >/dev/null
case "$("$kg" search --limit 1 2>/dev/null || true)" in *'error: "search requires QUERY"'*) ;; *) exit 1;; esac
printf 'kg index tests: passed\n'
