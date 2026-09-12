# Copilot CLI on Real Infrastructure

**The agent borrows your access. Scope what it borrows.**

GitHub Copilot CLI has no cloud permissions of its own. It runs commands as you,
in a shell that already holds your credentials. This lab shows you what that means
and which flags actually change it.

Four short steps, about 30 minutes. You will break a deny rule on purpose, watch an
agent read a file you did not mean to share, and learn the difference between an
agent *deciding* not to do something and an agent *not being allowed* to.

Nothing here touches a real cloud. Every cloud command in the lab is a fake.

**You need:** macOS or Linux (on Linux, `bwrap` 0.5.0+), Git, and
[Copilot CLI](https://docs.github.com/en/copilot/how-tos/copilot-cli/set-up-copilot-cli/install-copilot-cli)
with an active subscription — **updated first**: run `copilot update` and check
`copilot --version`. This lab is verified on **1.0.84-5**. Older builds rename the
write tools: 1.0.83 rejected `edit` and `create` as unknown tool names, which is
the sort of thing you want to discover now, not mid-lab.

---

## Step 0 — Get the lab

```bash
git clone https://github.com/adilshehzad786/copilot-cli-real-infra.git
cd copilot-cli-real-infra/lab     # already inside a checkout? just: cd lab

export PATH="$PWD/stubs:$PATH"
gcloud --version
```

You should see `DEMO_STUB_EXECUTED: fake gcloud`. Every cloud command name here —
`gcloud`, `terraform`, `kubectl`, `aws` and nine more — is a symlink to a four-line script that
prints that marker and exits. Nothing in this lab can reach a cloud API.

That is a safety net for the lab, not a security boundary. Your real credentials
are still on this machine, which is the whole point of what follows.

**Every later step assumes you are in `lab/`.** Check now, and check again after
opening a new terminal:

```bash
ls policy/
```

You should see `read-only.json` and `read-write.json`. If you see
`No such file or directory` instead, you are one directory up — `cd lab`.

## Step 1 — Three flags

No config files. Just three flags that do three different jobs:

| Flag | What it does |
|---|---|
| `--available-tools` | Which tools the model can see at all |
| `--allow-tool` | Which ones it can use **without asking you** |
| `--deny-tool` | Which ones it may never use |

Start a session that can read but not touch anything:

```bash
copilot --available-tools=view,grep,glob --allow-tool=read --deny-tool=write,shell
```

Ask it:

> Read evidence/ci-failure.log and .github/workflows/ci.yml. Why did this run fail?

It should tell you the workflow never asked for an OIDC token — it is missing
`id-token: write`.

**Now notice what did not happen.** It read a workflow, a log and a directory tree,
and never once asked your permission.

That is not because of `--allow-tool=read` — read-only operations are approved
automatically, with or without it. The flag records your intent; it does not cause
the behaviour. "Nothing happens without your approval" really means "nothing
*destructive* happens without your approval."

Ask it one more thing:

> Read ../docs/answers.md

It will not just do it. You get a path-approval prompt, or a refusal — even though
`view` is an allowed tool and nothing in your flags mentions files.

That is a **third control you did not set**: file access defaults to the current
directory and below. It is not one of your three flags, and no flag on that line
turned it on.

Two things follow. Your flags were never the whole story. And this control *asks* —
so anyone can approve it away in a second. Step 2 is about the kind that does not
ask.

## Step 2 — A policy that actually denies something

Flags control *tools*. To control *paths and network*, Copilot needs a settings
file. `COPILOT_HOME` picks which config directory it reads.

```bash
# pwd must end in /lab — both lines below depend on it.
echo 'DEMO_SENTINEL=synthetic-not-a-secret' > .env

export LAB_HOME="$(mktemp -d)"
sed "s|__LAB__|$PWD|g; s|__HOME__|$HOME|g" policy/read-only.json > "$LAB_HOME/settings.json"
```

That policy limits reads to this directory, turns off network access, and denies
`.env` plus your real credential directories by name.

Read the result before you trust it:

```bash
grep '__LAB__\|__HOME__' "$LAB_HOME/settings.json" && echo "STOP: substitution failed" || echo "policy ready"
```

You want `policy ready` — real absolute paths, no placeholders. If the `sed` line
itself failed with `No such file or directory`, you are not in `lab/` (see Step 0)
and the session below would start with **no policy at all** — the one state where
nothing in this step can be denied.

Be clear about which half is load-bearing: because the policy grants *only* this
directory, `~/.aws` and `~/.ssh` were already unreachable — the grant list did
that, not the deny list. The denial that does real work here is `.env`, inside the
directory you granted.

```bash
COPILOT_HOME="$LAB_HOME" copilot --experimental --sandbox \
  --disable-builtin-mcps \
  --available-tools=view,grep,glob --allow-tool=read --deny-tool=write,shell
```

`--disable-builtin-mcps` earns its place from this step on: the policy blocks
outbound network, so the built-in GitHub MCP server would fail to connect and
print a red error over the top of your session. Nothing in the lab uses it.

Type `/sandbox` to see the current state, then ask for the same file again:

> Read ../docs/answers.md

This time there is no prompt to approve. It is refused, and you cannot wave it
through. The refusal is explicit and names the layer — verified on 1.0.83:

> ✗ Read answers.md (sandbox policy)
> └ Outside the sandbox's readable paths. Run /sandbox to review or widen the sandbox policy.

That line is the wall. If you see the file's *contents* instead, the policy never
loaded — stop and re-check the substitution above.

Now try the fake secret:

> Read .env

If the model declines by *citing the repository rules* rather than hitting a wall,
that is not the sandbox — that is Step 3's lesson arriving early. Worth noticing.

> **What `--experimental` actually does.** It registers the `/sandbox` command —
> without it, `/sandbox` answers `Unknown command`. It does not turn enforcement
> on. The policy is already live because `settings.json` says `"enabled": true`.
> Enforcement lives in the config; introspection lives behind the flag.

## Step 3 — Refusing is not the same as being stopped

This is the step that matters. Run it in the **same terminal as Step 2** — the
command reads `$LAB_HOME`, and a new terminal does not have it.

```bash
COPILOT_HOME="$LAB_HOME" copilot --experimental --sandbox \
  --disable-builtin-mcps \
  --available-tools=view,grep,glob,bash \
  --allow-tool='shell(az)' \
  --deny-tool='write,shell(gcloud),shell(gcloud:*)'
```

Ask four things in order:

**1. "Skip Terraform and fix the bucket in GCP directly."**
It should decline, because `AGENTS.md` tells it not to. That is the model
*choosing* to follow instructions. Nothing stopped it.

**2. "Run `az --version`."**
It runs, and prints `DEMO_STUB_EXECUTED: fake az`. This proves the fake command is
real and reachable, and that the model does what you ask.

**3. "Run `gcloud --version`."**
Same shape. Same fake binary behind it. Denied, and the refusal names the rules:
`shell(gcloud)` and `shell(gcloud:*)`.

Only the third one is a permission boundary. Without the second, a working deny
produces no output at all — and you could not tell a denial from a model that
quietly decided not to bother.

**4. "Run `bash -c 'gcloud --version'`."**
`bash` is available but not pre-approved, so you get an approval prompt. Approve
it, and watch `DEMO_STUB_EXECUTED: fake gcloud` appear — in the same session that
just refused `gcloud` by name.

Nothing is broken. The rule named a string, and you handed it a different string.
A deny rule matches a command, not an authority.

Note why the allow rule is `shell(az)` and not `shell(az --version)`: patterns
match the command and its subcommands, not the whole command line. A flag is not
a subcommand, so the longer pattern matches nothing and you get a prompt instead
of the clean contrast.

> **Quote the parentheses.** `--deny-tool=shell(git push)` unquoted is a syntax
> error in bash and zsh. Quote from the `=` onward: `--deny-tool='shell(git push)'`.

## Step 4 — Propose a change

Writes are not in `--allow-tool`, so the first edit has to ask you.

Two things changed from Step 3. The policy is swapped for the read-write one, or
every edit would be blocked. And `shell` is denied outright — the agent does not
need it here, and git run *inside* the sandbox would fail anyway, because `.git`
sits at the clone root, outside the one directory the policy grants. You run git
yourself, in your own shell, where none of this applies.

Same terminal again — this reuses `$LAB_HOME`:

```bash
sed "s|__LAB__|$PWD|g; s|__HOME__|$HOME|g" policy/read-write.json > "$LAB_HOME/settings.json"
grep -q 'readwritePaths.*\[\]' "$LAB_HOME/settings.json" && echo "STOP: still read-only" || echo "policy swapped"

git switch -c my-hardening

COPILOT_HOME="$LAB_HOME" copilot --experimental --sandbox \
  --disable-builtin-mcps \
  --available-tools=view,grep,glob,edit,create \
  --deny-tool='shell,write(.env)'
```

Ask:

> Review terraform/main.tf against AGENTS.md. Name each risk in one line, then fix
> the file in place.

Approve the first write when it asks. Then, from a second terminal:

```bash
git --no-pager diff
```

Four things should change: the `allUsers` grant goes, public access prevention
becomes explicit, uniform access on, versioning on. **The first one is the point** —
uniform bucket-level access alone *sounds* like hardening and would have left the
bucket public.

Expected answers: [docs/answers.md](docs/answers.md).

### Reset

```bash
git checkout . && git switch main && git branch -D my-hardening
```

---

## What you just learned

**Visibility is not permission.** `--available-tools` decides what the model can
see; `--allow-tool` decides whether you get interrupted. An allow rule cannot bring
back a tool you hid.

**Deny beats allow**, including `--allow-all` and any approval you saved earlier.

**A pattern is not an intent.** `shell(gcloud)` matches the command name;
`shell(gcloud:*)` matches it as a prefix, so it catches `gcloud storage ...` too.
The boundary is the stem, which is why `shell(git:*)` never matches `gitea`.

What no spelling catches is Step 3's fourth probe: `bash -c 'gcloud --version'`.
Nor a script the agent writes and then runs, nor a differently-named CLI, nor an
MCP server calling the API directly. You are naming strings, not authority.

**Reading is the risk.** In a codebase with anything sensitive in it, exfiltration
never needed write access.

GitHub says the quiet part out loud in its own help text — run `copilot help sandbox`:

> Note that the sandbox still inherits your shell environment apart from a fixed
> blocklist, so other credentials already present in your environment (for example
> `AWS_ACCESS_KEY_ID`) remain visible to sandboxed commands.

One more default worth knowing: `allowDevToolAccess` is **on** unless you turn it
off, and it grants read access to developer config files — including registry
tokens like `~/.npmrc`. This lab turns it off. In August 2026 the setting was
renamed from `allowDevToolCaches`, and old spellings are ignored silently, so an
existing opt-out quietly reverted to permissive. Defaults move; check yours.

## Doing this for real

1. Run the agent somewhere disposable that holds only what the task needs — no
   personal credential store, no SSH agent, no cloud metadata identity.
2. If it needs cloud access, give it a narrow, short-lived credential minted
   *outside* that environment. An impersonation flag is configuration, not
   isolation, while the stronger credential is still reachable.
3. Keep changes as pull requests. Let CI hold the deployment identity, and never
   let untrusted PR code inherit it.

Deny rules are the speed bump on the honest path. IAM is the wall.

## Notes

- **The lab is deliberately broken.** A security scanner is supposed to flag it.
  See [SECURITY.md](SECURITY.md) for what is intentional and why.
- **What is verified and what is not.** Checked by running Copilot CLI **1.0.83**
  and **1.0.84-5**: the deny rules and their error text, the `bash -c` wrapper
  bypass, the fact that `shell(az --version)` does not match while `shell(az)`
  does, that path access defaults to the working directory, that `deniedPaths`
  works only under `userPolicy.filesystem`, and that enforcement comes from
  `settings.json` rather than `--experimental`. Also observed: `shell(gcloud:*)`
  matches a bare `gcloud` with no arguments (the stem-plus-space reading of the
  docs is wrong on these builds — denying both spellings is belt-and-braces, not
  load-bearing); a grant-only `userPolicy.filesystem` policy also removed the
  default home-directory read (`~/.zshrc` was blocked with no deny rule naming
  it); and fresh `COPILOT_HOME` directories authenticated without a login step on
  this machine — with one transient failure window that a retry cleared, so
  pre-warm profiles before a demo. Builds move fast and rename things: `edit` and
  `create` are the write-tool names on 1.0.84-5, 1.0.83 called them unknown, and
  neither build has tools named `write` or `apply_patch` — `--deny-tool=write`
  is a permission *kind*, not a tool name, and is accepted as one. Taken from
  GitHub's documentation and *not* observed: deny-vs-allow precedence, the
  `--excluded-tools` interaction, and the hook short-circuit. Model wording varies
  between runs — if yours differs, trust what you saw.
- Prompts to copy: [docs/prompts.txt](docs/prompts.txt). Slides:
  [copilot-cli-real-infra-deck.pptx](copilot-cli-real-infra-deck.pptx).
