#!/usr/bin/env bash
# Offline verification: no Copilot model calls, cloud APIs, or provider downloads.
set -euo pipefail
lab_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"
for lab_script in "$lab_root"/demo/sessions/*.sh "$lab_root"/scripts/*.sh; do
  bash -n "$lab_script"
done
python3 -m unittest discover -s "$lab_root/tests" -p 'test_*.py' -v
