#!/usr/bin/env bash
# Confirm every beat would launch, without starting a session, creating a
# branch, or consuming a login. Run this before stage day.
set -uo pipefail
lab_root="$(cd -- "$(dirname -- "${BASH_SOURCE[0]}")/.." && pwd)"

if [ -z "${DEMO_WORKSPACE:-}" ]; then
  echo "DEMO_WORKSPACE is not set. Run:" >&2
  echo '  export DEMO_WORKSPACE="$(python3 scripts/setup-demo.py --parent ~/talk-lab)"' >&2
  exit 2
fi

status=0
for beat in a b c; do
  if python3 "$lab_root/scripts/launch-demo.py" "$beat" --preflight; then
    echo
  else
    echo "PREFLIGHT FAIL for beat $beat" >&2
    echo
    status=1
  fi
done

dirty="$(git -C "$DEMO_WORKSPACE" status --porcelain)"
if [ -n "$dirty" ]; then
  echo "Estate is NOT clean. Beat B will refuse to launch on it." >&2
  echo "Keep it for its diff and create a new one with scripts/setup-demo.py." >&2
  printf '%s\n' "$dirty" >&2
  status=1
else
  echo "Estate is clean: $DEMO_WORKSPACE"
fi

branch="$(git -C "$DEMO_WORKSPACE" branch --show-current)"
[ "$branch" = "main" ] || { echo "Estate is on '$branch', not main. Create a new estate." >&2; status=1; }

exit "$status"
