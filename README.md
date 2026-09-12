# Copilot CLI on Real Infrastructure

**The agent borrows your access. Scope what it borrows.**

A 20-minute talk and an offline lab about what an AI coding agent can reach on a
machine that holds cloud credentials, which controls actually constrain it, and
where those controls stop.

There are no launcher scripts. Every step is the real `copilot` command with its
real flags, because the permission flags *are* the lesson.

| | |
|---|---|
| [docs/lab-guide.md](docs/lab-guide.md) | **The lab, command by command** |
| [docs/prompts.txt](docs/prompts.txt) | Paste-ready prompts for each beat |
| [docs/answers.md](docs/answers.md) | Expected results — read after, not before |
| [presentations/](presentations/README.md) | The 12-slide deck and how to rebuild it |
| [TALK-SCRIPT.md](TALK-SCRIPT.md) | The spoken argument |
| [TALK-RUNSHEET.md](TALK-RUNSHEET.md) | Stage-day clock and recovery |
| [docs/VERIFICATION.md](docs/VERIFICATION.md) | What is documented, what is tested, what is not |

## The claim

Copilot CLI holds no cloud permissions of its own. When it runs `gcloud`, gcloud
authenticates. When it runs a client library, the library goes looking for
credentials and finds yours. The question is never "what can the agent do" — it is
"whose authority can each tool reach from this shell."

On a laptop that can mean an active gcloud login, Application Default Credentials,
a kubeconfig, or an SSH agent. A remote MCP server is different again: it runs off
your machine and may authenticate as a principal you never see.

Unsetting one variable does not produce an empty credential environment. ADC falls
back from `GOOGLE_APPLICATION_CREDENTIALS` to a well-known file and then to a
metadata service. See the
[ADC search order](https://docs.cloud.google.com/docs/authentication/application-default-credentials).

## Run it

**Requires macOS or Linux.** The lab's policy sets `deniedPaths`, which the Windows
sandbox backend cannot enforce. Also needs Git, and
[Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli)
with an active subscription. Ideally a disposable VM with no cloud credentials.

```bash
git clone https://github.com/adilshehzad786/copilot-cli-real-infra.git
cd copilot-cli-real-infra

cp -R lab ~/copilot-lab && cd ~/copilot-lab
git init -q && git add -A && git commit -qm "lab baseline"
echo 'DEMO_SENTINEL=synthetic-not-a-secret' > .env
export PATH="$PWD/stubs:$PATH"

export RO="$(mktemp -d)" RW="$(mktemp -d)"
sed "s|__LAB__|$PWD|g; s|__HOME__|$HOME|g" policy/read-only.json  > "$RO/settings.json"
sed "s|__LAB__|$PWD|g; s|__HOME__|$HOME|g" policy/read-write.json > "$RW/settings.json"
```

Then the three beats:

```bash
# A — read. No shell at all, no writes, four tools.
COPILOT_HOME="$RO" copilot --experimental --sandbox \
  --available-tools=view,grep,glob \
  --allow-tool=read \
  --deny-tool=write,shell

# B — write. Editing tools available; writes deliberately NOT pre-approved.
git switch -c demo/harden-bucket
COPILOT_HOME="$RW" copilot --experimental --sandbox \
  --available-tools=view,grep,glob,bash,edit,create,apply_patch \
  --allow-tool='read,shell(git status),shell(git diff)' \
  --deny-tool='shell(git push),shell(git commit),shell(terraform),shell(terraform:*),shell(gcloud),shell(gcloud:*)'

# C — refuse. One cloud command allowed as a control, one denied.
COPILOT_HOME="$RO" copilot --experimental --sandbox \
  --available-tools=view,grep,glob,bash \
  --allow-tool='read,shell(az --version)' \
  --deny-tool='write,shell(gcloud),shell(gcloud:*)'
```

Inspect `/sandbox status` and `/sandbox policy` before typing a prompt. If the
policy is inactive or does not deny `.env`, stop.

Full walkthrough: [docs/lab-guide.md](docs/lab-guide.md).

**Quote the parentheses.** `--deny-tool=shell(git push)` unquoted is a hard syntax
error in both bash and zsh.

## What the three beats show

| Beat | Task | What it proves |
|---|---|---|
| A: read | Diagnose a synthetic CI failure | The workflow never requested an OIDC token — and nothing prompted for any of those reads |
| B: write | Harden the bucket configuration | A write approval, a branch, a reviewable diff. Uniform access alone would leave the public IAM grant in place |
| C: refuse | Ask for a direct cloud fix, then run two identical commands | A model declining is not a permission boundary. One allowed probe reaches the stub; one denied probe does not |

`lab/stubs/` is thirteen symlinks to one four-line shell script, so every cloud
command name in the lab is inert. `az --version` prints `DEMO_STUB_EXECUTED` and
proves the fake binary is reachable; `gcloud --version` is identical in shape and
denied. Without that control, a working deny produces no output and nobody can
tell enforcement from a model that quietly declined.

## Where the controls live

Seven configurable controls sit on one layer no vendor setting touches: the
credentials your shell already holds.

| Control | Question it answers | Limit to remember |
|---|---|---|
| Runtime identity and reachable credentials | What can authenticate? | Includes MCP identities and token-minting authority |
| Tool visibility | Which tools can the model select? | An exposed shell is general-purpose |
| Tool permission | Does this invocation prompt, or match a deny? | A pattern is not a security intent |
| Path permission | Which locations may a tool access? | Distinct from OS sandbox enforcement |
| URL permission | Which destinations are approved? | Distinct from network isolation |
| Local sandbox | What can this operation read, write, or contact? | Public preview; inspect the resolved policy |
| Hooks and enterprise settings | What does trusted policy code decide? | A `permissionRequest` hook decides *before* the normal rules |

**Visibility is not permission.** `--available-tools` changes what the model can
select; `--allow-tool` changes whether you are asked. An allow cannot restore a
hidden tool. Pass both `--available-tools` and `--excluded-tools` and the former
wins while the latter is ignored.

**Deny beats allow** — including `--allow-all` and saved approvals — within the
normal rules engine. A `permissionRequest` hook can decide before that engine runs.

**`:*` matches the stem plus a space.** `shell(git:*)` catches `git push`; it does
not catch `gitea`, and it does not catch a bare `git`. That is why the lab denies
both `shell(gcloud)` and `shell(gcloud:*)`.

## What the sandbox does and does not cover

Local sandboxing is public preview and needs `--experimental`.

By default a sandboxed process can write in the working directory and temporary
folders, and can **read your entire home directory** plus system and tool
locations. So `cd terraform/` scopes your writes and not your reads — the
repository was never the boundary. Explicit denials are the only thing that removes
a path, which is why `policy/*.json` names `~/.aws`, `~/.config/gcloud`,
`~/.config/gh`, `~/.kube` and `~/.ssh`. Note what that is: someone enumerating what
they happened to think of.

Three documented edges: built-in file tools check policy in-process with no OS
backstop; remote MCP servers run off your machine and the filesystem policy does
not constrain them; the feature is subject to change. Credit where due — escaping
the sandbox always requires interactive human confirmation, and a hook cannot
pre-approve it.

**Approvals do not expire alike.** Tool approvals save to `permissions-config.json`
scoped to the Git root. An approved URL domain goes into `allowedUrls` in
`settings.json` and applies to every session using that config directory,
indefinitely. CLI flags last one invocation. This is why the lab uses fresh
`COPILOT_HOME` directories.

## Applying this to real work

1. Run the agent in a disposable runtime holding only what the task needs — no
   personal credential store, SSH agent, container socket, or metadata identity.
2. If it needs cloud reads, grant task-specific permissions on narrow resources.
   Project-wide `roles/viewer` is not a least-privilege recipe; reads disclose data.
3. Mint bounded credentials *outside* the runtime. An impersonation flag is
   configuration, not isolation, while the stronger credential stays reachable.
4. Separate proposal from deployment. Give CI its own identity with federation
   conditions tied to the repository, and never let untrusted pull-request code
   inherit an apply identity.

## Honest status

The lab's workflow and bucket are broken on purpose, and the workflow deliberately
holds a federated identity while running pull-request Terraform — named from the
stage rather than quietly fixed, because it is the same borrowed-access story.

Product behaviour here comes from GitHub's documentation. **Copilot CLI was not run
during the review that produced this repository**, so approval dialogs, sandbox
enforcement and pattern matching are recorded as unverified in
[docs/VERIFICATION.md](docs/VERIFICATION.md). Fill those in from your own rehearsal
before presenting any of it as observed. If something differs on stage, say what
you actually saw.
