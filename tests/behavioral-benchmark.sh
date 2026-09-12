#!/bin/sh
set -eu

repo_root=$(CDPATH= cd -- "$(dirname -- "$0")/.." && pwd)
"$repo_root/scripts/behavioral-benchmark" --verify >/dev/null
