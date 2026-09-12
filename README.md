# Copilot CLI on Real Infrastructure

**The agent borrows your access. Scope what it borrows.**

A 20-minute talk and a local lab about what an AI coding agent can reach on a
machine that holds cloud credentials, which controls actually constrain it, and
where those controls stop.

The lab runs offline. It builds a throwaway Git repository containing a
deliberately broken CI workflow and an unhardened Terraform bucket, then launches
GitHub Copilot CLI against it three times with three different permission
configurations. No GCP project, no deployment, and no real credentials are
involved at any point.

| | |
|---|---|
| [Run the lab](#run-the-lab) | Setup and the three demo beats |
| [demo/README.md](demo/README.md) | Prompts, expected results, and what each beat proves |
| [presentations/](presentations/README.md) | The 12-slide deck and how to rebuild it |
| [TALK-SCRIPT.md](TALK-SCRIPT.md) | The spoken argument |
| [TALK-RUNSHEET.md](TALK-RUNSHEET.md) | Stage-day clock, checklists, recovery |
| [docs/VERIFICATION.md](docs/VERIFICATION.md) | What is documented, what was tested, what is not |
| [docs/REVIEW.md](docs/REVIEW.md) | Review history and the defects that are deliberate |

## The claim

Copilot CLI holds no cloud permissions of its own. When it runs `gcloud`, gcloud
authenticates. When it runs a client library, the library finds credentials. The
question is never "what can the agent do" — it is "whose authority can each tool
reach from this shell."

On a developer laptop that can mean an active gcloud login, Application Default
Credentials, a kubeconfig, an SSH agent, or a metadata identity. A remote MCP
server is different again: it runs off your machine and may authenticate as a
principal you never see.

Unsetting one environment variable does not produce an empty credential
environment. ADC falls back from `GOOGLE_APPLICATION_CREDENTIALS` to a well-known
file and then to a metadata service. See the
[ADC search order](https://docs.cloud.google.com/docs/authentication/application-default-credentials).

## Run the lab

### Prerequisites

- **macOS or Linux.** The lab's sandbox policy sets `deniedPaths`, which the
  Windows backend cannot enforce, and Windows sandboxing needs an Insiders build.
  On Windows, use a Linux VM or container.
- Python 3.9+, Git, and Bash.
- [Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli)
  and an active Copilot subscription — needed only for steps 3 onward.
  An organization or enterprise admin can disable the CLI outright, so check
  policy before debugging a token.
- Ideally a disposable VM holding no cloud credentials. The launcher rebuilds the
  session environment, but your OS user and home directory still apply.

### 1. Check the harness

```bash
git clone https://github.com/adilshehzad786/copilot-cli-real-infra.git
cd copilot-cli-real-infra
./scripts/check-lab.sh
```

Runs the offline test suite. It exercises our launcher against a stub, not
GitHub's permission engine, and needs no Copilot install.

### 2. Create a throwaway estate

```bash
export DEMO_WORKSPACE="$(python3 scripts/setup-demo.py --parent ~/talk-lab)"
echo "$DEMO_WORKSPACE"
```

Creates a new temporary Git repository on `main` with a baseline commit, no
remote, and only the fixture files. `--parent ~/talk-lab` keeps the path short
enough to read from a projector; omit it for the system temp directory.

Nothing is ever initialised, reset, or committed in this repository. To start
over, run the command again — the old estate stays on disk with its diff intact.

### 3. Confirm all three beats will launch

```bash
./scripts/preflight.sh
```

Checks the CLI version, required flags, sandbox backend and estate state for
every beat without starting a session, creating a branch, or consuming a login.
Do this before stage day, not ten minutes before.

### 4. Run the beats

```bash
./demo/sessions/a-read-only.sh        # inspect: diagnose the CI failure
./demo/sessions/b-propose-change.sh   # propose: harden the bucket on a branch
./demo/sessions/c-refuse.sh           # distinguish: refusal vs. enforcement
```

Each launch prints its exact flags, generates a fresh `COPILOT_HOME` so no saved
approval from an earlier run is in scope, and writes a sandbox policy. **Inspect
`/sandbox status` and `/sandbox policy` before typing a prompt.** If the policy is
inactive or does not deny `.env` and tool network access, stop.

The prompts and the expected evidence for each beat are in
[demo/README.md](demo/README.md).

After beat B, review the diff from a separate shell:

```bash
git -C "$DEMO_WORKSPACE" --no-pager diff -- terraform/main.tf
```

Nothing commits, pushes, opens a pull request, or applies infrastructure.

## What the three beats show

| Beat | Task | What it proves |
|---|---|---|
| A: inspect | Diagnose a synthetic CI failure | The workflow never requested an OIDC token — and nothing prompted for any of those reads |
| B: propose | Harden the bucket configuration | A write approval, a branch, and a reviewable diff. Uniform access alone would leave the public IAM grant in place |
| C: distinguish | Ask for a direct cloud fix, then probe two identical commands | A model declining is not a permission boundary. One allowed probe reaches the local stub; one denied probe does not |

Beat C is the one worth rehearsing. `az --version` is allow-listed and prints
`DEMO_STUB_EXECUTED`, proving the fake binary is real and reachable. The
identically shaped `gcloud --version` is denied. Same command shape, same stub,
one deny rule between them — which is what makes the denial visible instead of
being an absence of output.

## Where the controls live

Seven configurable controls sit on top of one layer no vendor setting touches:
the identity and credentials your shell already holds.

| Control | Question it answers | Limit to remember |
|---|---|---|
| Runtime identity and reachable credentials | What can authenticate? | Includes MCP identities and token-minting authority |
| Tool visibility | Which tools can the model select? | An exposed shell is general-purpose |
| Tool permission | Does this invocation prompt, or match a deny? | A pattern is not a security intent |
| Path permission | Which locations may a tool access? | Distinct from OS sandbox enforcement |
| URL permission | Which destinations are approved? | Distinct from network isolation |
| Local sandbox | What can this operation read, write, or contact? | Public preview; inspect the resolved policy |
| Hooks and enterprise settings | What does trusted policy code decide? | A `permissionRequest` hook decides *before* the normal rules |

Three specifics that matter more than the map:

**Visibility is not permission.** `--available-tools` changes what the model can
select; `--allow-tool` changes whether you are asked. An allow cannot restore a
hidden tool. Pass both `--available-tools` and `--excluded-tools` and the former
wins while the latter is ignored.

**Deny beats allow** — including `--allow-all` and saved approvals — within the
normal rules engine. A `permissionRequest` hook can return a decision before that
engine runs, so your hooks are inside your trust boundary.

**`:*` matches the stem plus a space.** `shell(git:*)` catches `git push`; it does
not catch `gitea`, and it does not catch a bare `git`. This lab denies both
`shell(gcloud)` and `shell(gcloud:*)` for that reason.

## What the sandbox does and does not cover

Local sandboxing is in public preview and needs `--experimental`.

By default a sandboxed process can write in the working directory and temporary
folders, and can **read your entire home directory** plus system and tool
locations. In a Git repository the rest of the repo above your working directory
is readable too. So `cd terraform/` scopes your writes and not your reads, and
explicit denials are the only thing that removes a path. That is why this lab's
generated policy denies `~/.aws`, `~/.config/gcloud`, `~/.config/gh`, `~/.kube`
and `~/.ssh` by absolute path.

Three documented edges: the built-in file tools check policy in-process with no OS
backstop; remote MCP servers run off your machine and the filesystem policy does
not constrain them; and the feature is subject to change. Credit where it is due —
escaping the sandbox always requires interactive human confirmation, and a hook
cannot pre-approve it.

**Approvals do not expire alike.** Tool approvals save to
`permissions-config.json` scoped to the Git root. A permanently approved URL
domain goes into `allowedUrls` in `settings.json` and applies to every session
using that configuration, indefinitely. CLI flags last one invocation.
`/reset-allowed-tools` clears saved tool grants for the current location; it does
not touch URL grants.

## Applying this to real work

Recommendations, not infrastructure implemented here.

1. Run the agent in a disposable runtime holding only the code and data the task
   needs — no personal credential store, SSH agent, container socket, or
   unintended metadata identity.
2. If it needs cloud reads, grant task-specific permissions on narrow resources.
   Project-wide `roles/viewer` plus log access is not a least-privilege recipe;
   reads disclose data.
3. Mint bounded credentials *outside* the runtime. An impersonation flag is
   configuration, not isolation, while the stronger source credential remains
   reachable.
4. Separate proposal from deployment. Give CI its own identity with federation
   conditions tied to the intended repository, protect branches, environments and
   workflow files, and never let untrusted pull-request code inherit an apply
   identity.

## Honest status

The lab's workflow and bucket are broken on purpose. This repository does not
implement a production plan/apply pipeline, WIF trust policy, branch rules, or
cloud IAM — present those as a pattern, not as a fourth demo.

Product behaviour here is sourced from GitHub's documentation and from offline
tests of our own launcher. **Copilot CLI was not run during the review that
produced this repository**, so approval dialogs, sandbox enforcement and
command-pattern matching are recorded as unverified. Fill in
[docs/VERIFICATION.md](docs/VERIFICATION.md) from your own rehearsal before
presenting any of it as an observed result. If something differs on stage,
describe what you actually saw.
