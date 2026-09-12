#!/usr/bin/env python3
"""Launch one interactive Copilot rehearsal with fresh settings and permissions.

  python3 scripts/launch-demo.py a            # start beat A
  python3 scripts/launch-demo.py b --preflight # check beat B would launch, then stop

--preflight runs every readiness check and exits without starting a session,
creating no branch and consuming no login. Use it before the talk: the
alternative is discovering a problem by starting all three beats, which burns
three logins and permanently dirties the estate for beat B.
"""
import argparse
import os
from pathlib import Path
import platform
import shlex
import shutil
import subprocess
import sys
import tempfile
import uuid

from lab import (COMMON_FLAGS, TOOL_FLAGS, git, session_environment,
                 validate_estate, write_policy)


def check_host():
    """Seatbelt or Bubblewrap only.

    This is not a claim that Copilot lacks a Windows sandbox -- it uses
    ProcessContainer there. It is that this lab's policy sets deniedPaths, which
    the Windows backend cannot enforce (the policy is rejected and the sandboxed
    command fails), and Windows sandboxing additionally requires an Insiders
    build. So the lab requires a macOS or Linux host.
    """
    system = platform.system()
    if system == "Darwin" and Path("/usr/bin/sandbox-exec").is_file():
        return "macOS Seatbelt"
    if system == "Linux" and shutil.which("bwrap"):
        return "Linux Bubblewrap"
    raise ValueError(
        "This lab's policy sets deniedPaths, which the Windows sandbox backend "
        "cannot enforce, and Windows sandboxing needs an Insiders build. Use a "
        "macOS (Seatbelt) or Linux (Bubblewrap) host; do not disable the sandbox.")


def check_cli(copilot, estate, env):
    """Confirm the installed build advertises the flags the beats depend on.

    Both `copilot --help` and `copilot help` are searched: the command reference
    says the complete option list comes from `copilot help`, and the sandbox
    flags are experimental, so an abbreviated `--help` is a plausible build. A
    miss on an experimental flag is a warning rather than a hard stop, so a
    supported CLI whose help text merely changed shape cannot abort the talk.
    """
    surfaces = []
    for argv in (["--help"], ["help"]):
        try:
            result = subprocess.run([str(copilot), *argv], cwd=estate, env=env,
                                    capture_output=True, text=True, timeout=30)
            surfaces.append(result.stdout + result.stderr)
        except (OSError, subprocess.SubprocessError):
            continue
    if not surfaces:
        raise ValueError("Could not run Copilot to inspect its help output.")
    text = "\n".join(surfaces)
    required = ["--available-tools", "--allow-tool", "--deny-tool"]
    missing = [flag for flag in required if flag not in text]
    if missing:
        raise ValueError("Installed Copilot help lacks required flags: "
                         + ", ".join(missing))
    return [flag for flag in COMMON_FLAGS if flag not in text]


def main():
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("beat", choices=TOOL_FLAGS)
    parser.add_argument("--preflight", action="store_true",
                        help="Run every readiness check, then exit without "
                             "starting a session or creating a branch.")
    args = parser.parse_args()
    estate = validate_estate(os.environ.get("DEMO_WORKSPACE"))
    executable = shutil.which("copilot")
    if not executable:
        raise ValueError("Copilot CLI is not installed or not on PATH. "
                         "Offline checks: scripts/check-lab.sh")
    copilot = Path(executable).absolute()
    backend = check_host()

    # Beat B's preconditions are checked before anything is written, so a refused
    # launch leaves no session directory, no stub tree and no policy behind.
    branch = os.environ.get("DEMO_BRANCH", "demo/harden-bucket-" + uuid.uuid4().hex[:10])
    if args.beat == "b":
        if git(estate, "status", "--porcelain").stdout.strip():
            raise ValueError(
                "Beat B requires a clean estate, and this one has already been "
                "rehearsed. Keep it for its diff and run scripts/setup-demo.py "
                "to create a new one.")
        if not branch.startswith("demo/") or git(
                estate, "check-ref-format", "--branch", branch, check=False).returncode:
            raise ValueError("DEMO_BRANCH must be a valid branch name beginning with demo/.")
        if git(estate, "rev-parse", "--verify", "--quiet", "refs/heads/" + branch,
               check=False).returncode == 0:
            raise ValueError("Branch " + branch + " already exists. Set DEMO_BRANCH "
                             "to a new name, or create a fresh estate.")

    session = Path(tempfile.mkdtemp(prefix="session-" + args.beat + ".", dir=estate.parent))
    try:
        env = session_environment(session, copilot)
        policy = write_policy(estate, session, args.beat)
        experimental_gaps = check_cli(copilot, estate, env)
        version = subprocess.run([str(copilot), "--version"], cwd=estate, env=env,
                                 check=True, capture_output=True, text=True,
                                 timeout=30).stdout.strip()
    except BaseException:
        # Never leave a read/write policy behind for a session that never ran:
        # it is indistinguishable from the real one when collecting evidence.
        shutil.rmtree(session, ignore_errors=True)
        raise

    user_policy = policy["sandbox"]["userPolicy"]
    command = [str(copilot), *COMMON_FLAGS, *TOOL_FLAGS[args.beat]]
    banner = [
        "Copilot version: " + (version or "<no version reported>"),
        "Sandbox backend: " + backend,
        "Estate: " + str(estate),
        "Fresh COPILOT_HOME: " + env["COPILOT_HOME"],
        "Writable paths: " + (", ".join(user_policy["readwritePaths"]) or "(none)"),
        "Denied paths: " + str(len(user_policy["deniedPaths"])) + " -> "
        + ", ".join(user_policy["deniedPaths"]),
        "Tool network: outbound off, local off",
        "Command: " + shlex.join(command),
    ]
    if experimental_gaps:
        banner.append("WARNING: help text did not mention " + ", ".join(experimental_gaps)
                      + ". Record the version and confirm support before presenting.")
    # Keep the banner readable after the session scrolls it away: `cat` this file
    # into the terminal before the beat so the flags are on screen.
    (estate.parent / ("banner-" + args.beat + ".txt")).write_text("\n".join(banner) + "\n")

    if args.preflight:
        print("\n".join(banner), flush=True)
        print("\nPREFLIGHT PASS for beat " + args.beat
              + ". No session started, no branch created.", flush=True)
        shutil.rmtree(session, ignore_errors=True)
        return 0

    if args.beat == "b":
        git(estate, "checkout", "-b", branch)
    print("\n".join(banner), flush=True)
    print("Branch: " + (git(estate, "branch", "--show-current").stdout.strip() or "DETACHED"),
          flush=True)
    print("Before the prompt: inspect /sandbox status and /sandbox policy. Stop if "
          "policy is inactive, invalid, or does not deny .env and tool network.", flush=True)
    print("Synthetic fixtures only. Your OS user and HOME still apply; use a "
          "disposable host with no cloud credentials. Log in if this session asks.",
          flush=True)
    result = subprocess.run(command, cwd=estate, env=env)
    # A signal death returns a negative code; sys.exit(-2) would become 254.
    return result.returncode if result.returncode >= 0 else 128 - result.returncode


if __name__ == "__main__":
    try:
        sys.exit(main())
    except KeyboardInterrupt:
        print("\nSession interrupted.", file=sys.stderr)
        sys.exit(130)
    except subprocess.CalledProcessError as exc:
        detail = (exc.stderr or "").strip()
        sys.exit("Lab launch failed (exit " + str(exc.returncode) + "): " + detail)
    except (OSError, ValueError, subprocess.TimeoutExpired) as exc:
        sys.exit("Lab launch failed: " + str(exc))
