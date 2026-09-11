#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
ruby "$repo_root/scripts/behavioral-benchmark.rb" --verify >/dev/null
