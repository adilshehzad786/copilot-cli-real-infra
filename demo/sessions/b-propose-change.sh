#!/usr/bin/env bash
# Local rehearsal only. See demo/README.md for the prompt and evidence criteria.
set -euo pipefail
lab_scripts="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/../../scripts" && pwd)"
exec python3 "$lab_scripts/launch-demo.py" b "$@"
