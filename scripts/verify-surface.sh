#!/bin/sh
# Scoped verification for one named source surface.
#
# `make verify` lists the surfaces and the focused tests each one runs;
# `make verify-SURFACE` runs the shared lint, type, graph, and whitespace gates
# and then only those focused offline tests. This is an iteration gate for the
# affected surface. `make test` remains the final repository acceptance gate
# before handoff, and this script never replaces it.
set -eu

here=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)

# The one surface map: `<surface> <focused test files...>`. The focused files are
# the offline tests that cover the surface, so a change there fails here long
# before the full suite runs. `memory` keeps its files as one glob because the
# memory-evaluation harness is split across sibling modules.
mapping() {
	cat <<'EOF'
storage tests/test_store.py tests/test_identity.py tests/test_vault.py tests/test_migration.py tests/test_tangle_foundation.py tests/test_tangle_verification.py tests/test_tangle_reconcile.py
index tests/test_tangle_index.py tests/test_index_upkeep.py tests/test_views.py tests/test_cluster_verbs.py tests/test_packet.py tests/test_node_references.py tests/test_orphan_warning.py
check tests/test_graph_check.py tests/test_revision.py tests/test_orphan_warning.py tests/test_manifest.py
intake tests/test_feedback_record.py tests/test_feedback_scan.py tests/test_decompose.py tests/test_scaffold.py
cli tests/test_launchers.py tests/test_scaffold.py tests/test_skill.py
semantic tests/test_semantic.py tests/test_provider.py tests/test_clustering.py tests/test_reduction.py tests/test_cluster_verbs.py
memory tests/test_memory_*.py
benchmarks tests/test_behavioral_benchmark.py tests/test_embedding_benchmark.py tests/test_quality_benchmark.py tests/test_staged_benchmark.py tests/test_token_benchmark.py tests/test_storage_comparison.py tests/test_verb_benchmark.py
EOF
}

surface_names() {
	mapping | while read -r name _files; do
		echo "$name"
	done
}

surface_files() {
	mapping | while read -r name files; do
		if [ "$name" = "$1" ]; then
			echo "$files"
		fi
	done
}

if [ "$#" -eq 0 ]; then
	echo "Scoped verification surfaces, each run after the lint, type, graph,"
	echo "and whitespace gates:"
	mapping | while read -r name files; do
		echo
		echo "$name"
		echo "  $files"
	done
	exit 0
fi

if [ "$1" = "--list" ]; then
	surface_names
	exit 0
fi

surface=$1
files=$(surface_files "$surface")
if [ -z "$files" ]; then
	echo "verify-surface: unknown surface: $surface" >&2
	echo "valid surfaces: $(surface_names | tr '\n' ' ')" >&2
	exit 2
fi

# The benchmark suite is opt-in and carries its own pytest marker, exactly as
# the full benchmark target runs it.
markers=
if [ "$surface" = "benchmarks" ]; then
	markers="-m benchmark"
fi

cd "$here"

echo "== lint =="
uv run ruff check

echo
echo "== type =="
uv run mypy

echo
echo "== graph =="
./scripts/tangle check

echo
echo "== whitespace =="
git diff --check

echo
echo "== focused tests: $surface =="
# shellcheck disable=SC2086  # an unquoted list expands the files and the glob
uv run pytest -q $markers $files
