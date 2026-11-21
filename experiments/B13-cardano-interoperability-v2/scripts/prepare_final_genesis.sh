#!/usr/bin/env bash
set -euo pipefail

# Delegate to the shared generator, which refuses existing genesis material.
project_dir="$(cd "$(dirname "${BASH_SOURCE[0]}")/.." && pwd)"
exec python3 "$project_dir/../../scripts/prepare-genesis.py" "$project_dir" "$@"
