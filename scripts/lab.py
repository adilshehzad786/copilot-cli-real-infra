"""Small, standard-library-only helpers for the local rehearsal harness."""
import json
import os
from pathlib import Path
import shutil
import subprocess

ROOT = Path(__file__).resolve().parent.parent
FIXTURES = (
    "AGENTS.md", ".gitignore", "terraform/main.tf",
    ".github/workflows/ci.yml", "evidence/ci-failure.log",
)
MARKER = ".copilot-infra-lab.json"

# Every cloud/infra command name the beats might reach by bare name. Each becomes
# a copy of demo/stubs/cloud-command, so an invocation that slips past a deny rule
# hits an inert local script instead of a real SDK. gsutil, bq and the Terraform
# wrappers are here because a GCP-shaped prompt reaches for them by habit.
STUBBED = ("gcloud", "gsutil", "bq", "kubectl", "helm", "terraform", "tofu",
           "terragrunt", "aws", "az", "gh", "docker", "cloud-sql-proxy")

# Home-directory paths worth denying explicitly when they exist. Deny-listing
# named dotfiles is exactly the pattern this talk criticises -- it enumerates
# what you thought of -- so treat it as a floor, not a boundary, and prefer a
# runtime that holds no credentials at all.
# The only variables forwarded from the presenter's shell. Everything else the
# session needs is rebuilt below, so an inherited token or SDK override cannot
# reach a projected session. The proxy and CA entries are here because login
# fails behind a corporate or conference proxy without them -- they carry no
# credential, and the test suite asserts this exact set.
PASSED_THROUGH = ("HOME", "USER", "LOGNAME", "TERM", "COLORTERM", "LANG", "LC_ALL",
                  "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy",
                  "https_proxy", "no_proxy", "NODE_EXTRA_CA_CERTS")

CREDENTIAL_PATHS = (
    ".aws", ".azure", ".config/gcloud", ".config/gh", ".config/git", ".kube",
    ".ssh", ".gitconfig", ".netrc", ".git-credentials", ".docker", ".npmrc",
    ".terraform.d", ".gnupg", ".boto", "Library/Keychains",
)


def git(estate, *args, check=True):
    # Do not load global hooks, signing, credential helpers, aliases, or templates.
    env = {key: value for key, value in os.environ.items()
           if not key.startswith("GIT_")}
    env.update(GIT_CONFIG_NOSYSTEM="1", GIT_CONFIG_GLOBAL=os.devnull,
               GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0")
    return subprocess.run(
        ["git", "-c", "core.hooksPath=" + os.devnull,
         "-c", "commit.gpgsign=false", "-c", "tag.gpgsign=false", *args],
        cwd=estate, env=env, check=check, text=True, capture_output=True,
    )


def validate_estate(raw):
    if not raw:
        raise ValueError("DEMO_WORKSPACE is required; run scripts/setup-demo.py first.")
    candidate = Path(raw).expanduser()
    if candidate.is_symlink():
        raise ValueError("DEMO_WORKSPACE must not be a symbolic link.")
    estate = candidate.resolve(strict=True)
    lab_root = estate.parent
    marker = lab_root / MARKER
    if marker.is_symlink() or not marker.is_file():
        raise ValueError("Not a generated demo estate (missing lab marker).")
    metadata = json.loads(marker.read_text())
    if metadata != {"schema": 1, "estate": str(estate)}:
        raise ValueError("Lab marker does not match this estate.")
    if not (estate / ".git").is_dir():
        raise ValueError("The generated estate must have its own Git directory.")
    for path in estate.rglob("*"):
        if path.is_symlink():
            raise ValueError("Symbolic links are not supported in the rehearsal estate.")
    for relative in (*FIXTURES, ".env"):
        if not (estate / relative).is_file():
            raise ValueError("Missing required fixture: " + relative)
    if git(estate, "rev-parse", "--show-toplevel").stdout.strip() != str(estate):
        raise ValueError("The estate is not the root of its own Git repository.")
    if git(estate, "remote").stdout.strip():
        raise ValueError("The rehearsal estate must have no Git remotes.")
    return estate


def session_environment(session, copilot):
    """Remove inherited credentials/config; retain the OS user's real HOME.

    This is accident prevention, not an OS identity or sandbox boundary.
    """
    config = session / "copilot"
    empty = session / "empty-config"
    stub_bin = session / "bin"
    for path in (config, empty, stub_bin, session / "tmp"):
        path.mkdir()
    for name in STUBBED:
        shutil.copyfile(ROOT / "demo/stubs/cloud-command", stub_bin / name)
        (stub_bin / name).chmod(0o755)
    for name in ("kubeconfig", "aws-config", "aws-credentials"):
        (empty / name).touch(mode=0o600)
    for name in ("gcloud", "azure", "gh", "xdg"):
        (empty / name).mkdir()
    env = {key: os.environ[key] for key in PASSED_THROUGH if key in os.environ}
    # PATH is the stub directory plus the system default path. The Copilot
    # executable and the Node runtime are linked INTO the stub directory rather
    # than having their parent directories appended: on a Homebrew or npm-global
    # install those parents are the user's main bin directory, and appending it
    # would put every installed tool -- gsutil, bq, cloud-sql-proxy, psql -- back
    # on PATH by bare name, which would make "stubs first on PATH" nearly
    # meaningless. This still leaves the system default path (/usr/bin and
    # friends) reachable, because the beats need git and ordinary shell tools.
    # It is accident prevention, not an isolation boundary; see demo/README.md.
    for source in (copilot, Path(shutil.which("node") or os.devnull)):
        link = stub_bin / source.name
        if source.is_file() and not link.exists():
            link.symlink_to(source)
    env.update(
        PATH=os.pathsep.join([str(stub_bin), os.defpath]),
        COPILOT_HOME=str(config),
        TMPDIR=str(session / "tmp"), XDG_CONFIG_HOME=str(empty / "xdg"),
        CLOUDSDK_CONFIG=str(empty / "gcloud"),
        GOOGLE_APPLICATION_CREDENTIALS=str(empty / "no-google-adc.json"),
        GCE_METADATA_HOST="127.0.0.1:9", GCE_METADATA_IP="127.0.0.1",
        AWS_SHARED_CREDENTIALS_FILE=str(empty / "aws-credentials"),
        AWS_CONFIG_FILE=str(empty / "aws-config"), AWS_EC2_METADATA_DISABLED="true",
        AZURE_CONFIG_DIR=str(empty / "azure"), KUBECONFIG=str(empty / "kubeconfig"),
        GH_CONFIG_DIR=str(empty / "gh"), GIT_CONFIG_NOSYSTEM="1",
        GIT_CONFIG_GLOBAL=os.devnull, GIT_TERMINAL_PROMPT="0", GIT_OPTIONAL_LOCKS="0",
    )
    return env


def write_policy(estate, session, beat):
    denied = [estate / ".env", session / "copilot"]
    user_home = Path.home()
    denied.extend(path for relative in CREDENTIAL_PATHS
                  if (path := user_home / relative).exists())
    readonly = [str(session / "bin")] + ([str(estate)] if beat != "b" else [])
    readwrite = [str(estate)] if beat == "b" else []
    # The user-scope spelling of the path grants is NOT documented. The only
    # published schema that names readonlyPaths/readwritePaths is the enterprise
    # managed-settings reference, which nests them under userPolicy.filesystem.
    # We emit both spellings so a build that honours either one gets the intended
    # policy, and neither is asserted as correct: /sandbox policy and the
    # /settings Problems tab are the only evidence that settles it. See the
    # "Sandbox path-grant key spelling" row in docs/VERIFICATION.md.
    policy = {
        "sandbox": {
            "enabled": True, "allowBypass": False,
            "addCurrentWorkingDirectory": False, "allowDevToolAccess": False,
            "sandboxMcpServers": True, "sandboxLspServers": True,
            "auth": {"git": False, "gh": False},
            "userPolicy": {
                "readonlyPaths": readonly,
                "readwritePaths": readwrite,
                "filesystem": {"readonlyPaths": readonly,
                               "readwritePaths": readwrite},
                "deniedPaths": [str(path) for path in denied],
                "network": {"allowOutbound": False, "allowLocalNetwork": False},
                "seatbelt": {"keychainAccess": False},
            },
        },
    }
    target = session / "copilot/settings.json"
    target.write_text(json.dumps(policy, indent=2) + "\n")
    target.chmod(0o600)
    return policy


COMMON_FLAGS = [
    "--experimental", "--sandbox", "--disable-builtin-mcps",
    "--no-bash-env", "--no-auto-update", "--disallow-temp-dir",
]

# Command stems that must never mutate anything in this lab.
BLOCKED_COMMANDS = ("terraform", "tofu", "terragrunt", "gcloud", "gsutil", "bq",
                    "kubectl", "helm", "aws", "az", "docker", "gh")
BLOCKED_GIT = ("git push", "git commit", "git remote")


def deny_patterns(commands, skip=()):
    """Both spellings of a command deny, because one of them is not enough.

    GitHub documents the `:*` suffix as matching the command stem followed by a
    space -- `shell(git:*)` matches `git push` and `git pull`, but not `gitea`,
    and not a bare `git` with no arguments. A deny list written only with `:*`
    therefore lets an argument-less invocation fall through to an ordinary
    approval prompt. Emitting `shell(cmd)` alongside `shell(cmd:*)` closes that.
    """
    patterns = []
    for command in commands:
        if command in skip:
            continue
        patterns.extend(["shell(" + command + ")", "shell(" + command + ":*)"])
    return patterns


def _flag(name, values):
    return "--" + name + "=" + ",".join(values)


# Beat C keeps `az` un-denied on purpose: it is the experiment's positive
# control. `az --version` is allow-listed, reaches the local stub and prints
# DEMO_STUB_EXECUTED, which proves the fake binary is real and reachable. The
# identically shaped `gcloud --version` is denied. Without that control, a
# working deny produces no output at all and the audience cannot tell a denial
# from a model that quietly declined.
CONTROL_COMMAND = "az"

TOOL_FLAGS = {
    "a": ["--available-tools=view,grep,glob",
          "--allow-tool=read",
          "--deny-tool=write,shell"],
    "b": ["--available-tools=view,grep,glob,bash,edit,create,apply_patch",
          "--allow-tool=read,shell(git status),shell(git diff)",
          _flag("deny-tool", [*("shell(" + g + ")" for g in BLOCKED_GIT),
                              "shell(git remote:*)",
                              *deny_patterns(BLOCKED_COMMANDS)])],
    "c": ["--available-tools=view,grep,glob,bash",
          "--allow-tool=read,shell(" + CONTROL_COMMAND + " --version)",
          _flag("deny-tool", ["write",
                              *("shell(" + g + ")" for g in BLOCKED_GIT),
                              "shell(git remote:*)",
                              *deny_patterns(BLOCKED_COMMANDS,
                                             skip=(CONTROL_COMMAND,))])],
}
