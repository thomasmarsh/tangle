.PHONY: test benchmark diagnostic-benchmark storage-comparison

test:
	sh tests/skill.sh
	sh tests/graph-check.sh
	sh tests/install.sh
	sh tests/behavioral-benchmark.sh
	sh tests/token-benchmark.sh
	sh tests/storage-comparison.sh
	sh tests/worktree-parallel.sh
	sh tests/kg-foundation.sh
	sh tests/kg-index.sh
	sh tests/kg-verification.sh
	git diff --check

benchmark:
	ruby scripts/token-benchmark.rb --protocol

diagnostic-benchmark:
	ruby scripts/behavioral-benchmark.rb --verify

storage-comparison:
	ruby scripts/storage-comparison.rb --verify
