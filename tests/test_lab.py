"""Offline harness tests: these exercise our launcher, never the Copilot engine.

What these can establish: the disposable estate is built correctly, the launch
contract is exactly what we intend, the child environment is a real allowlist,
and every refusal path stops before a session starts. What they cannot establish:
anything about GitHub's permission matcher, the sandbox implementation, or model
behaviour. Those live in docs/VERIFICATION.md and stay Unverified until someone
records them on a real CLI.

The assertions deliberately compare against literals spelled out in this file
rather than against the constants in lab.py. Asserting that lab.py matches
lab.py passes no matter what lab.py says, which would let a one-line edit turn
the stage demo into an unsandboxed session with a green test run.
"""
import json
import os
from pathlib import Path
import subprocess
import sys
import tempfile
import unittest

ROOT = Path(__file__).resolve().parents[1]
sys.path.insert(0, str(ROOT / "scripts"))
from lab import COMMON_FLAGS, FIXTURES, STUBBED, git  # noqa: E402

EXPECTED_COMMON_FLAGS = ["--experimental", "--sandbox", "--disable-builtin-mcps",
                         "--no-bash-env", "--no-auto-update", "--disallow-temp-dir"]
EXPECTED_FIXTURES = {"AGENTS.md", ".gitignore", "terraform/main.tf",
                     ".github/workflows/ci.yml", "evidence/ci-failure.log"}
# Every variable the child is allowed to receive. Anything outside this set is a
# leak from the presenter's shell into a session that gets projected.
# macOS injects __CF_USER_TEXT_ENCODING into child processes; it is a locale
# hint set by the OS, not something inherited from the presenter's shell.
PLATFORM_INJECTED = {"__CF_USER_TEXT_ENCODING"}
EXPECTED_ENV = {
    "HOME", "USER", "LOGNAME", "TERM", "COLORTERM", "LANG", "LC_ALL",
    "HTTP_PROXY", "HTTPS_PROXY", "NO_PROXY", "http_proxy", "https_proxy",
    "no_proxy", "NODE_EXTRA_CA_CERTS",
    "PATH", "COPILOT_HOME", "TMPDIR", "XDG_CONFIG_HOME", "CLOUDSDK_CONFIG",
    "GOOGLE_APPLICATION_CREDENTIALS", "GCE_METADATA_HOST", "GCE_METADATA_IP",
    "AWS_SHARED_CREDENTIALS_FILE", "AWS_CONFIG_FILE", "AWS_EC2_METADATA_DISABLED",
    "AZURE_CONFIG_DIR", "KUBECONFIG", "GH_CONFIG_DIR", "GIT_CONFIG_NOSYSTEM",
    "GIT_CONFIG_GLOBAL", "GIT_TERMINAL_PROMPT", "GIT_OPTIONAL_LOCKS",
}


class LabTests(unittest.TestCase):
    def setUp(self):
        self.temporary = tempfile.TemporaryDirectory(prefix="lab-check.")
        self.addCleanup(self.temporary.cleanup)
        self.base = Path(self.temporary.name).resolve()
        self.bin = self.base / "tools"
        self.bin.mkdir()
        self.capture = self.base / "copilot-calls.jsonl"
        self.fake = self.bin / "copilot"
        self.write_copilot()
        # A stub backend only makes the launcher's host check portable. No
        # sandbox is invoked, and nothing here tests sandbox enforcement.
        backend = self.bin / "bwrap"
        backend.write_text("#!/bin/sh\nexit 0\n")
        backend.chmod(0o755)
        self.env = os.environ.copy()
        self.env["PATH"] = str(self.bin) + os.pathsep + os.environ.get("PATH", os.defpath)
        setup = subprocess.run([sys.executable, str(ROOT / "scripts/setup-demo.py"),
                                "--parent", str(self.base)], env=self.env,
                               capture_output=True, text=True, check=True)
        self.estate = Path(setup.stdout.strip())
        self.env["DEMO_WORKSPACE"] = str(self.estate)
        self.unrelated = self.base / "unrelated directory"
        self.unrelated.mkdir()

    def write_copilot(self, exit_code=0, help_flags=None):
        """A fake CLI that answers help/version and records every real session."""
        flags = help_flags if help_flags is not None else [
            *COMMON_FLAGS, "--available-tools", "--allow-tool", "--deny-tool"]
        self.fake.write_text(
            "#!" + sys.executable + "\n"
            "import json, os, pathlib, sys\n"
            "if sys.argv[1:] in (['--help'], ['help']):\n"
            "    print(" + repr(" ".join(flags)) + "); sys.exit(0)\n"
            "if sys.argv[1:] == ['--version']:\n"
            "    print('test-stub; NOT Copilot'); sys.exit(0)\n"
            "with pathlib.Path(" + repr(str(self.capture)) + ").open('a') as capture:\n"
            "    capture.write(json.dumps({'cwd': os.getcwd(), 'argv': sys.argv[1:],"
            " 'env': dict(os.environ)}) + '\\n')\n"
            "sys.exit(" + str(exit_code) + ")\n"
        )
        self.fake.chmod(0o755)

    def launch(self, beat, extra=(), env=None):
        return subprocess.run([sys.executable, str(ROOT / "scripts/launch-demo.py"),
                               beat, *extra], cwd=self.unrelated,
                              env=env or self.env, capture_output=True, text=True)

    def calls(self):
        return [json.loads(line) for line in self.capture.read_text().splitlines()]

    def assert_no_session(self):
        self.assertFalse(self.capture.exists(), "Copilot session unexpectedly started")

    @staticmethod
    def flag(argv, name):
        """Every value passed for one flag, so a duplicate cannot hide."""
        return [arg.split("=", 1)[1] for arg in argv if arg.startswith(name + "=")]

    # --- estate construction -------------------------------------------------

    def test_setup_is_fresh_separate_git_repo_with_only_fixtures(self):
        self.assertEqual(git(self.estate, "branch", "--show-current").stdout.strip(), "main")
        self.assertEqual(git(self.estate, "status", "--porcelain").stdout, "")
        self.assertEqual(git(self.estate, "remote").stdout, "")
        tracked = set(git(self.estate, "ls-files").stdout.splitlines())
        self.assertEqual(tracked, EXPECTED_FIXTURES)
        self.assertEqual(set(FIXTURES), EXPECTED_FIXTURES)
        self.assertTrue((self.estate / ".env").is_file())  # Do not read the sentinel.
        self.assertEqual(git(self.estate, "check-ignore", ".env").returncode, 0)
        self.assertFalse((self.estate / "answers").exists())
        self.assertFalse((self.estate / "README.md").exists())
        again = subprocess.run([sys.executable, str(ROOT / "scripts/setup-demo.py"),
                                "--parent", str(self.base)], capture_output=True,
                               text=True, check=True)
        self.assertNotEqual(Path(again.stdout.strip()), self.estate)
        self.assertTrue(self.estate.is_dir())

    def test_workflow_and_bucket_remain_intentionally_broken(self):
        workflow = (self.estate / ".github/workflows/ci.yml").read_text()
        hcl = (self.estate / "terraform/main.tf").read_text()
        evidence = (self.estate / "evidence/ci-failure.log").read_text()
        # Assert the absent grant, not the bare string: a comment mentioning
        # id-token would satisfy a substring check while also handing the model
        # the answer.
        self.assertIn("permissions:\n  contents: read\n", workflow)
        self.assertNotIn("id-token: write", workflow)
        self.assertIn('member = "allUsers"', hcl)
        self.assertIn("force_destroy = true", hcl)
        self.assertNotIn("uniform_bucket_level_access", hcl)
        self.assertNotIn("public_access_prevention", hcl)
        self.assertIn("SYNTHETIC FIXTURE", evidence)
        self.assertIn("ACTIONS_ID_TOKEN_REQUEST_URL", evidence)

    def test_provider_has_no_inline_credentials(self):
        """Beat A's story is 'no token, no plan'.

        The Google provider resolves ADC at configure time, so a plan fails
        without credentials -- but only while the provider block stays free of an
        inline credentials or access_token argument.
        """
        hcl = (self.estate / "terraform/main.tf").read_text()
        self.assertNotIn("credentials", hcl)
        self.assertNotIn("access_token", hcl)

    # --- launch contract -----------------------------------------------------

    def test_common_flags_are_exactly_the_sandboxed_set(self):
        self.assertEqual(COMMON_FLAGS, EXPECTED_COMMON_FLAGS)

    def test_every_beat_passes_its_exact_tool_contract(self):
        expectations = {
            "a": {"available": "view,grep,glob", "allow": "read",
                  "denied": ["write", "shell"], "absent": []},
            "b": {"available": "view,grep,glob,bash,edit,create,apply_patch",
                  "allow": "read,shell(git status),shell(git diff)",
                  "denied": ["shell(git push)", "shell(gcloud)", "shell(gcloud:*)",
                             "shell(terraform)", "shell(terraform:*)",
                             "shell(gsutil)", "shell(bq)", "shell(az)"],
                  "absent": []},
            "c": {"available": "view,grep,glob,bash",
                  "allow": "read,shell(az --version)",
                  "denied": ["write", "shell(gcloud)", "shell(gcloud:*)",
                             "shell(terraform)", "shell(terragrunt)"],
                  # az stays un-denied on purpose: it is the positive control.
                  "absent": ["shell(az)", "shell(az:*)"]},
        }
        for beat, expected in expectations.items():
            with self.subTest(beat=beat):
                self.capture.unlink(missing_ok=True)
                self.assertEqual(self.launch(beat).returncode, 0)
                argv = self.calls()[0]["argv"]
                self.assertEqual(self.flag(argv, "--available-tools"),
                                 [expected["available"]])
                self.assertEqual(self.flag(argv, "--allow-tool"), [expected["allow"]])
                denied = self.flag(argv, "--deny-tool")
                self.assertEqual(len(denied), 1, "exactly one deny flag")
                patterns = denied[0].split(",")
                for pattern in expected["denied"]:
                    self.assertIn(pattern, patterns)
                for pattern in expected["absent"]:
                    self.assertNotIn(pattern, patterns)
                self.assertTrue(set(EXPECTED_COMMON_FLAGS).issubset(argv))

    def test_deny_rules_cover_the_bare_command_as_well_as_the_wildcard(self):
        """`shell(x:*)` matches the stem plus a space, so a bare `x` needs its own rule."""
        self.assertEqual(self.launch("c").returncode, 0)
        patterns = self.flag(self.calls()[0]["argv"], "--deny-tool")[0].split(",")
        for command in ("gcloud", "terraform", "kubectl", "gsutil", "bq"):
            self.assertIn("shell(" + command + ")", patterns)
            self.assertIn("shell(" + command + ":*)", patterns)

    def test_beat_a_resolves_cwd_and_writes_a_sandbox_policy(self):
        result = self.launch("a")
        self.assertEqual(result.returncode, 0, result.stderr)
        call = self.calls()[0]
        self.assertEqual(call["cwd"], str(self.estate))
        settings = json.loads((Path(call["env"]["COPILOT_HOME"]) / "settings.json").read_text())
        sandbox = settings["sandbox"]
        self.assertTrue(sandbox["enabled"])
        self.assertFalse(sandbox["allowBypass"])
        self.assertFalse(sandbox["addCurrentWorkingDirectory"])
        self.assertFalse(sandbox["allowDevToolAccess"])
        self.assertEqual(sandbox["auth"], {"git": False, "gh": False})
        policy = sandbox["userPolicy"]
        self.assertEqual(policy["readwritePaths"], [])
        self.assertIn(str(self.estate), policy["readonlyPaths"])
        self.assertEqual(policy["network"],
                         {"allowOutbound": False, "allowLocalNetwork": False})
        self.assertIn(str(self.estate / ".env"), policy["deniedPaths"])
        self.assertIn(call["env"]["COPILOT_HOME"], policy["deniedPaths"])

    def test_policy_emits_both_documented_and_flat_path_spellings(self):
        """The user-scope spelling is undocumented; emit both until one is proven."""
        self.assertEqual(self.launch("b").returncode, 0)
        policy = json.loads((Path(self.calls()[0]["env"]["COPILOT_HOME"])
                             / "settings.json").read_text())["sandbox"]["userPolicy"]
        self.assertEqual(policy["readwritePaths"], [str(self.estate)])
        self.assertEqual(policy["filesystem"]["readwritePaths"], [str(self.estate)])
        self.assertEqual(policy["filesystem"]["readonlyPaths"], policy["readonlyPaths"])

    def test_policy_denies_credential_directories_that_exist(self):
        self.assertEqual(self.launch("a").returncode, 0)
        policy = json.loads((Path(self.calls()[0]["env"]["COPILOT_HOME"])
                             / "settings.json").read_text())["sandbox"]["userPolicy"]
        home = Path.home()
        for relative in (".aws", ".config/gcloud", ".config/gh", ".kube", ".ssh"):
            if (home / relative).exists():
                self.assertIn(str(home / relative), policy["deniedPaths"],
                              relative + " exists on this host but is not denied")

    def test_shell_entry_point_works_from_an_unrelated_directory(self):
        result = subprocess.run(
            ["bash", str(ROOT / "demo/sessions/a-read-only.sh")],
            cwd=self.unrelated, env=self.env, capture_output=True, text=True,
        )
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(self.calls()[0]["cwd"], str(self.estate))

    # --- environment ---------------------------------------------------------

    def test_child_environment_is_an_allowlist_not_a_denylist(self):
        decoys = {"AWS_ACCESS_KEY_ID": "synthetic", "AWS_SECRET_ACCESS_KEY": "synthetic",
                  "AZURE_CLIENT_SECRET": "synthetic", "GOOGLE_OAUTH_ACCESS_TOKEN": "x",
                  "GH_TOKEN": "x", "GITHUB_TOKEN": "x", "COPILOT_GITHUB_TOKEN": "x",
                  "SSH_AUTH_SOCK": "/tmp/agent", "BASH_ENV": "/tmp/profile",
                  "NODE_OPTIONS": "--require /tmp/x", "TF_VAR_project_id": "real-prod",
                  "VAULT_TOKEN": "x", "GOOGLE_CLOUD_PROJECT": "employer-prod",
                  "NPM_TOKEN": "x", "DOCKER_HOST": "tcp://host:2375"}
        # A proxy is forwarded on purpose; a token that looks like one is not.
        self.env["HTTPS_PROXY"] = "http://proxy.example.invalid:8080"
        self.env.update(decoys)
        self.env["COPILOT_HOME"] = str(self.base / "personal-copilot")
        self.env["CLOUDSDK_CONFIG"] = str(self.base / "personal-gcloud")
        result = self.launch("a")
        self.assertEqual(result.returncode, 0, result.stderr)
        child = self.calls()[0]["env"]
        self.assertEqual(set(child) - EXPECTED_ENV - PLATFORM_INJECTED, set(),
                         "unexpected variables reached the session")
        for name in decoys:
            self.assertNotIn(name, child)
        self.assertNotEqual(child["COPILOT_HOME"], self.env["COPILOT_HOME"])
        self.assertNotEqual(child["CLOUDSDK_CONFIG"], self.env["CLOUDSDK_CONFIG"])
        self.assertEqual(child.get("HOME"), self.env.get("HOME"))
        self.assertEqual(child["AWS_EC2_METADATA_DISABLED"], "true")
        self.assertEqual(child["HTTPS_PROXY"], "http://proxy.example.invalid:8080")
        self.assertFalse(Path(child["GOOGLE_APPLICATION_CREDENTIALS"]).exists())

    def test_session_path_is_the_stub_directory_then_system_defaults(self):
        """The package-manager bin directory must not come back by the side door."""
        self.assertEqual(self.launch("c").returncode, 0)
        entries = self.calls()[0]["env"]["PATH"].split(os.pathsep)
        self.assertEqual(entries, [entries[0]] + os.defpath.split(os.pathsep))
        stub_bin = Path(entries[0])
        for name in STUBBED:
            self.assertTrue((stub_bin / name).is_file(), name + " is not stubbed")

    def test_new_sessions_do_not_reuse_saved_approvals(self):
        self.assertEqual(self.launch("a").returncode, 0)
        first = Path(self.calls()[0]["env"]["COPILOT_HOME"])
        (first / "permissions-config.json").write_text('{"synthetic": "previous session"}')
        self.assertEqual(self.launch("c").returncode, 0)
        second = Path(self.calls()[1]["env"]["COPILOT_HOME"])
        self.assertNotEqual(first, second)
        self.assertFalse((second / "permissions-config.json").exists())

    # --- refusals ------------------------------------------------------------

    def test_preflight_checks_everything_and_starts_nothing(self):
        result = self.launch("b", extra=["--preflight"])
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("PREFLIGHT PASS", result.stdout)
        self.assert_no_session()
        self.assertEqual(git(self.estate, "branch", "--show-current").stdout.strip(), "main")

    def test_beat_b_creates_branch_without_preapproving_write(self):
        self.env["DEMO_BRANCH"] = "demo/rehearsal"
        result = self.launch("b")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertEqual(git(self.estate, "branch", "--show-current").stdout.strip(),
                         "demo/rehearsal")
        allows = self.flag(self.calls()[0]["argv"], "--allow-tool")
        self.assertEqual(allows, ["read,shell(git status),shell(git diff)"])

    def test_existing_branch_failure_does_not_start_session(self):
        git(self.estate, "branch", "demo/already-exists")
        self.env["DEMO_BRANCH"] = "demo/already-exists"
        result = self.launch("b")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("already exists", result.stderr)
        self.assertEqual(git(self.estate, "branch", "--show-current").stdout.strip(), "main")
        self.assert_no_session()

    def test_refused_launch_leaves_no_session_directory_behind(self):
        git(self.estate, "branch", "demo/already-exists")
        self.env["DEMO_BRANCH"] = "demo/already-exists"
        self.assertNotEqual(self.launch("b").returncode, 0)
        leftovers = list(self.estate.parent.glob("session-*"))
        self.assertEqual(leftovers, [], "a refused launch wrote a session directory")

    def test_dirty_estate_is_preserved_and_blocks_beat_b(self):
        extra = self.estate / "keep-my-notes.txt"
        extra.write_text("retain this work")
        result = self.launch("b")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("clean estate", result.stderr)
        self.assertIn("setup-demo.py", result.stderr)
        self.assertEqual(extra.read_text(), "retain this work")
        self.assert_no_session()

    def test_missing_workspace_fails_with_setup_hint(self):
        self.env.pop("DEMO_WORKSPACE")
        result = self.launch("a")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("setup-demo.py", result.stderr)
        self.assert_no_session()

    def test_remote_blocks_launch_without_contacting_remote(self):
        git(self.estate, "remote", "add", "origin", "https://example.invalid/not-real.git")
        result = self.launch("c")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("no Git remotes", result.stderr)
        self.assert_no_session()

    def test_tampered_marker_blocks_launch(self):
        marker = self.estate.parent / ".copilot-infra-lab.json"
        marker.write_text(json.dumps({"schema": 1, "estate": "/somewhere/else"}) + "\n")
        result = self.launch("a")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("marker", result.stderr)
        self.assert_no_session()

    def test_fixture_symlink_blocks_launch(self):
        target = self.estate / "terraform/main.tf"
        target.unlink()
        target.symlink_to(self.base / "does-not-exist")
        result = self.launch("a")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("Symbolic links", result.stderr)
        self.assert_no_session()

    def test_cli_without_required_flags_fails_before_session(self):
        self.write_copilot(help_flags=["--help"])
        result = self.launch("a")
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("lacks required flags", result.stderr)
        self.assert_no_session()

    def test_missing_experimental_flag_warns_but_still_launches(self):
        """A help-text change must not abort the talk; a missing matcher flag must."""
        self.write_copilot(help_flags=["--available-tools", "--allow-tool", "--deny-tool"])
        result = self.launch("a")
        self.assertEqual(result.returncode, 0, result.stderr)
        self.assertIn("WARNING", result.stdout)
        self.assertIn("--sandbox", result.stdout)

    def test_extra_cli_override_is_rejected(self):
        result = self.launch("a", extra=["--no-sandbox"])
        self.assertNotEqual(result.returncode, 0)
        self.assertIn("unrecognized arguments", result.stderr)
        self.assert_no_session()

    def test_cli_failure_exit_status_is_preserved(self):
        self.write_copilot(exit_code=23)
        result = self.launch("c")
        self.assertEqual(result.returncode, 23, result.stderr)

    # --- the fake cloud commands --------------------------------------------

    def test_version_probe_is_local_and_every_other_invocation_fails(self):
        self.assertEqual(self.launch("c").returncode, 0)
        stub_bin = Path(self.calls()[0]["env"]["PATH"].split(os.pathsep)[0])
        for name in ("gcloud", "az", "terraform", "gsutil", "bq"):
            probe = subprocess.run([str(stub_bin / name), "--version"],
                                   capture_output=True, text=True)
            self.assertEqual(probe.returncode, 0, name)
            self.assertIn("DEMO_STUB_EXECUTED", probe.stdout)
            self.assertIn(name, probe.stdout, "the marker must name the command")
        mutation = subprocess.run([str(stub_bin / "gcloud"), "storage", "buckets",
                                   "update", "synthetic"], capture_output=True, text=True)
        self.assertEqual(mutation.returncode, 97)
        self.assertIn("execution are disabled", mutation.stderr)


if __name__ == "__main__":
    unittest.main()
