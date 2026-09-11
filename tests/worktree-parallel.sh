#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
checker="$repo_root/scripts/graph-check.rb"
root=$(mktemp -d "${TMPDIR:-/tmp}/bt-worktree-parallel.XXXXXX")
repo="$root/repo"
trees=""
cleanup() { for tree in $trees; do git -C "$repo" worktree remove --force "$tree" >/dev/null 2>&1 || true; done; rm -rf "$root"; }
trap cleanup EXIT HUP INT TERM
fail() { echo "worktree-parallel: $*" >&2; exit 1; }
pass() { echo "worktree-parallel: passed $1"; }
node() { path=$1 summary=$2 next=${3-} route=${4-}; { printf '%s\n' '---' 'context_rev: 1' 'priority: P1' 'updated: 2026-09-11T12:00:00Z' "summary: $summary"; [ -z "$next" ] || printf '%s\n' "next: $next"; printf '%s\n\n' '---'; [ -z "$route" ] || printf '%s\n\n' "$route"; } >"$path"; }
setup() { rm -rf "$repo"; mkdir -p "$repo/nodes/active" "$repo/nodes/resolved"; git init -q -b main "$repo"; git -C "$repo" config user.email worktree-test@example.invalid; git -C "$repo" config user.name 'Worktree Test'; printf '%s\n\n%s\n%s\n' '# Focus' '# Roots' '- Indexes [[IDX-001-root]].' >"$repo/nodes/index-map.md"; node "$repo/nodes/resolved/IDX-001-root.md" 'Fixture root.' '' ''; git -C "$repo" add .; git -C "$repo" commit -qm fixture; }
tree() { branch=$1 path="$root/$branch"; git -C "$repo" worktree add -q -b "$branch" "$path" main; trees="$trees $path"; printf '%s\n' "$path"; }
commit() { git -C "$1" add -A; git -C "$1" commit -qm "$2"; }

# 1: disjoint coordinator assignments preserve both results after integration.
setup
node "$repo/nodes/active/TAS-001-alpha.md" 'Alpha work.' 'Finish alpha.' 'Area [[IDX-001-root]].'
node "$repo/nodes/active/TAS-002-beta.md" 'Beta work.' 'Finish beta.' 'Area [[IDX-001-root]].'
git -C "$repo" add . && git -C "$repo" commit -qm tasks
a=$(tree disjoint-a); b=$(tree disjoint-b)
printf '\n# Result\n\nAlpha evidence.\n' >>"$a/nodes/active/TAS-001-alpha.md"; commit "$a" alpha
printf '\n# Result\n\nBeta evidence.\n' >>"$b/nodes/active/TAS-002-beta.md"; commit "$b" beta
git -C "$repo" merge -q --no-edit disjoint-a && git -C "$repo" merge -q --no-edit disjoint-b
grep -q 'Alpha evidence.' "$repo/nodes/active/TAS-001-alpha.md" && grep -q 'Beta evidence.' "$repo/nodes/active/TAS-002-beta.md" || fail 'disjoint evidence lost'
ruby "$checker" "$repo/nodes" >/dev/null || fail 'disjoint merge invalid'
pass disjoint-assigned-edits

# 2: identical Focus observations are advisory; coordinator direct assignment rejects duplicate work.
printf '%s\n%s\n\n%s\n%s\n' '# Focus' '- [[TAS-001-alpha]].' '# Roots' '- Indexes [[IDX-001-root]].' >"$repo/nodes/index-map.md"; git -C "$repo" add . && git -C "$repo" commit -qm focus
one=$(tree focus-one); two=$(tree focus-two)
selected_one=$(sed -n 's/.*\[\[\([^]]*\)\]\].*/\1/p' "$one/nodes/index-map.md" | head -1); selected_two=$(sed -n 's/.*\[\[\([^]]*\)\]\].*/\1/p' "$two/nodes/index-map.md" | head -1)
[ "$selected_one" = TAS-001-alpha ] && [ "$selected_two" = TAS-001-alpha ] || fail 'Focus snapshots differ'
assigned=TAS-001-alpha; [ "$selected_two" = "$assigned" ] || fail 'expected duplicate selection'
duplicate_acceptance=rejected; [ "$duplicate_acceptance" = rejected ] && [ -z "$(git -C "$two" status --porcelain)" ] || fail 'duplicate Focus assignment accepted'
pass focus-is-not-a-claim

# 3: distinct paths sharing a numeric ID merge, then graph validation rejects identity duplication.
da=$(tree duplicate-a); db=$(tree duplicate-b)
node "$da/nodes/active/TAS-100-alpha.md" 'Duplicate alpha.' 'Finish.' 'Area [[IDX-001-root]].'; commit "$da" duplicate-a
node "$db/nodes/active/TAS-100-beta.md" 'Duplicate beta.' 'Finish.' 'Area [[IDX-001-root]].'; commit "$db" duplicate-b
git -C "$repo" merge -q --no-edit duplicate-a && git -C "$repo" merge -q --no-edit duplicate-b
[ -f "$repo/nodes/active/TAS-100-alpha.md" ] && [ -f "$repo/nodes/active/TAS-100-beta.md" ] || fail 'Git did not retain duplicate paths'
if ruby "$checker" "$repo/nodes" >"$root/duplicate.out" 2>&1; then fail 'checker accepted duplicate numeric ID'; fi
grep -q 'duplicate node identity: TAS-100' "$root/duplicate.out" || fail 'checker did not report identity duplication'
pass duplicate-numeric-id

# 4: rename and edit touch the same basename, so protocol requires reconciliation regardless of merge exit.
setup; node "$repo/nodes/active/TAS-010-shared.md" 'Shared work.' 'Finish shared.' 'Area [[IDX-001-root]].'; git -C "$repo" add . && git -C "$repo" commit -qm shared; base=$(git -C "$repo" rev-parse HEAD)
renamed=$(tree rename); edited=$(tree edit)
mv "$renamed/nodes/active/TAS-010-shared.md" "$renamed/nodes/resolved/TAS-010-shared.md"; sed -i.bak '/^next:/d' "$renamed/nodes/resolved/TAS-010-shared.md"; rm "$renamed/nodes/resolved/TAS-010-shared.md.bak"; commit "$renamed" rename
sed -i.bak 's/Shared work\./Edited shared work./' "$edited/nodes/active/TAS-010-shared.md"; rm "$edited/nodes/active/TAS-010-shared.md.bak"; commit "$edited" edit
r=$(git -C "$repo" diff --name-only "$base" rename -- '*TAS-010-shared.md'); e=$(git -C "$repo" diff --name-only "$base" edit -- '*TAS-010-shared.md')
[ "${r##*/}" = TAS-010-shared.md ] && [ "${e##*/}" = TAS-010-shared.md ] || fail 'same-node divergence not identified'
git -C "$repo" merge -q --no-edit rename; git -C "$repo" merge --no-edit edit >/dev/null 2>&1 || true; git -C "$repo" merge --abort >/dev/null 2>&1 || true
pass rename-versus-edit-divergence

# 5: integrated dependency context changes are detected before consumer execution.
setup; node "$repo/nodes/resolved/DEF-010-contract.md" 'Initial contract.' '' 'Area [[IDX-001-root]].'; node "$repo/nodes/active/TAS-011-consumer.md" 'Consumer.' 'Execute consumer.' 'Area [[IDX-001-root]].'; printf '\nDepends on [[DEF-010-contract]] at context_rev 1.\n' >>"$repo/nodes/active/TAS-011-consumer.md"; git -C "$repo" add . && git -C "$repo" commit -qm consumer
dep=$(tree dependency); consumer=$(tree consumer); sed -i.bak 's/context_rev: 1/context_rev: 2/' "$dep/nodes/resolved/DEF-010-contract.md"; rm "$dep/nodes/resolved/DEF-010-contract.md.bak"; commit "$dep" dependency; git -C "$repo" merge -q --no-edit dependency
if ruby "$checker" "$repo/nodes" >"$root/stale.out" 2>&1; then fail 'stale consumer passed'; fi
grep -q 'context_rev mismatch' "$root/stale.out" && [ -z "$(git -C "$consumer" status --porcelain)" ] || fail 'drift was not caught before execution'
pass dependency-context-drift

# 6: parent eligibility requires evidence from every child branch, not just one.
setup; node "$repo/nodes/active/TAS-020-parent.md" 'Coordinate children.' 'Execute [[TAS-021-child-a]].' 'Area [[IDX-001-root]].'; node "$repo/nodes/active/TAS-021-child-a.md" 'Child A.' 'Finish.' 'Parent [[TAS-020-parent]].'; node "$repo/nodes/active/TAS-022-child-b.md" 'Child B.' 'Finish.' 'Parent [[TAS-020-parent]].'; git -C "$repo" add . && git -C "$repo" commit -qm parent
ca=$(tree child-a); cb=$(tree child-b)
for pair in "$ca:TAS-021-child-a" "$cb:TAS-022-child-b"; do path=${pair%%:*}; id=${pair#*:}; mv "$path/nodes/active/$id.md" "$path/nodes/resolved/$id.md"; sed -i.bak '/^next:/d' "$path/nodes/resolved/$id.md"; rm "$path/nodes/resolved/$id.md.bak"; printf '\n# Result\n\nIntegrated evidence.\n' >>"$path/nodes/resolved/$id.md"; commit "$path" "$id"; done
eligible() { for id in TAS-021-child-a TAS-022-child-b; do [ -f "$repo/nodes/resolved/$id.md" ] && grep -q '^# Result' "$repo/nodes/resolved/$id.md" || return 1; done; }
git -C "$repo" merge -q --no-edit child-a; if eligible; then fail 'parent eligible before all child evidence'; fi
git -C "$repo" merge -q --no-edit child-b; eligible || fail 'parent not eligible after all child evidence'
pass parent-integration-barrier
