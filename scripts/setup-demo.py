#!/usr/bin/env python3
"""Create a new disposable lab; stdout is only the estate path for shell use."""
import argparse
import json
import os
from pathlib import Path
import shutil
import subprocess
import sys
import tempfile

from lab import FIXTURES, MARKER, ROOT, git


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--parent", type=Path,
                        help="Existing directory for a new temporary lab (default: system temp).")
    args = parser.parse_args()
    if not shutil.which("git"):
        raise ValueError("Git is required to create the disposable estate.")
    lab_root = Path(tempfile.mkdtemp(prefix="copilot-infra-lab.", dir=args.parent)).resolve()
    estate = lab_root / "estate"
    estate.mkdir(mode=0o700)
    for relative in FIXTURES:
        source = ROOT / "demo" / relative
        if source.is_symlink() or not source.is_file():
            raise ValueError("Fixture must be a regular file: " + relative)
        target = estate / relative
        target.parent.mkdir(parents=True, exist_ok=True)
        shutil.copyfile(source, target)
    # An intentionally synthetic sentinel. Never copy an existing .env.
    sentinel = estate / ".env"
    sentinel.write_text("DEMO_SENTINEL=synthetic-not-a-secret\n")
    sentinel.chmod(0o600)
    git(estate, "-c", "init.defaultBranch=main", "init", "--template=")
    git(estate, "add", "--", *FIXTURES)
    git(estate, "-c", "user.name=Local demo", "-c", "user.email=demo@example.invalid",
        "commit", "-m", "Synthetic lab baseline")
    (lab_root / MARKER).write_text(json.dumps({"schema": 1, "estate": str(estate)}) + "\n")
    print("Created a synthetic local estate with no remote. No cloud commands ran.", file=sys.stderr)
    print(estate)


if __name__ == "__main__":
    try:
        main()
    except subprocess.CalledProcessError as exc:
        sys.exit("Lab setup failed: " + (exc.stderr or str(exc)).strip())
    except (OSError, ValueError) as exc:
        sys.exit("Lab setup failed: " + str(exc))
