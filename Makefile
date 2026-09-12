.PHONY: test benchmark diagnostic-benchmark storage-comparison

test:
	uv run pytest -q
	uv run ruff check
	uv run mypy
	sh tests/graph-check.sh
	sh tests/install.sh
	sh tests/behavioral-benchmark.sh
	sh tests/token-benchmark.sh
	sh tests/storage-comparison.sh
	sh tests/worktree-parallel.sh
	sh tests/bt-foundation.sh
	sh tests/bt-index.sh
	sh tests/bt-verification.sh
	git diff --check

benchmark:
	uv run token-benchmark --protocol

diagnostic-benchmark:
	uv run behavioral-benchmark --verify

storage-comparison:
	uv run storage-comparison --verify
