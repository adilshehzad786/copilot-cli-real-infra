# Review history

Three passes.

## Pass 3 — the scripts came out

The lab used to be driven by Python launchers: `./demo/sessions/a-read-only.sh`
and four scripts behind it. That was the wrong shape for a talk. The permission
flags **are** the lesson, and a launcher hid every one of them — the audience saw
a bash script and learned nothing, and the presenter had nothing to point at.

Everything is now the real `copilot` command, typed in full.

What that exposed, which the scripts had been concealing:

- **Beat B's command was 642 characters with 28 deny patterns.** Tolerable only
  while hidden. Worse, it contradicted the talk's own slide 11 — "you enumerate
  what you thought of" reads badly beside a list that looks exhaustive. The deny
  lists are now short, projectable, and visibly incomplete, with the PATH stubs as
  the backstop and the talk saying so.
- **Shell quoting is a real hazard.** `--deny-tool=shell(git push)` unquoted is a
  hard syntax error in both bash and zsh. Python passed these as argv, so it never
  came up. Documented, with a recovery row in the runsheet.
- **`cp -R demo` would have handed the model its own answer key.** `answers/`,
  `prompts.txt` and the presenter guide all lived inside the directory that gets
  copied; the Python avoided it with an allowlist. `demo/` is now `lab/`,
  containing only what the agent may see, with presenter material in `docs/`. The
  safety is in the directory layout, where it is visible.
- **The stub tree is thirteen committed symlinks** to one four-line script, so
  `ls -l lab/stubs/` teaches the mechanism that a Python copy loop hid.
- **The sandbox policy is two committed JSON files** with `__LAB__`/`__HOME__`
  placeholders and one `sed` line, instead of generated JSON nobody could read.
- **Two `COPILOT_HOME` directories** replace per-launch generated ones. Switching
  profiles is now one visible environment variable, which is also the demonstration
  of the approval-persistence point on slide 9.

Removed: `scripts/` (five files), `lab/sessions/` (three), `tests/` (27 tests that
existed only to test the launchers), and `presentations/archive/`.

Losing the test suite is a real cost, recorded honestly: the harness it covered no
longer exists, and what remains is checkable by eye. The deck's `preview.py` still
fails the build on text overflow.

The three demo slides now carry the commands themselves, colour-coded — blue for
visibility, green for allow, red for deny.

## Passes 1 and 2

The first turned a feature-tour deck and a loose lab into an evidence-disciplined
one. The second fixed what that discipline broke and found the defects a static
read had missed.

### Pass 2 — 2026-09

Nine independent reviews (harness correctness, harness security, test quality,
Copilot product facts, GCP/CI facts, docs coherence, deck critique, stagecraft,
argument quality), each followed by an adversarial verifier that re-derived the
findings from the files. 92 findings; 76 confirmed, 13 judgement calls, 3 refuted.

#### The talk shrank to 20 minutes

Twelve slides, retimed end to end. Nine and a half minutes are live demo. The
install slide and the separate persistence slide are gone; "patterns, not intent"
and "IAM is the wall" merged into one slide, which is also where they belong
argumentatively — the pattern's fragility is the reason IAM matters.

#### Defects fixed

| Area | Defect | Fix |
|---|---|---|
| Deck | Two different decks shared the filename `copilot-cli-real-infra-deck.pptx`; the stale one sat at the repo root where a presenter looks first | One deck. The original is archived under a name that cannot be opened by accident |
| Deck | The only build path needed `@oai/artifact-tool`, available solely inside the OpenAI Codex runtime — the author could not rebuild their own deck | Rebuilt on `python-pptx`, plus `preview.py`, which renders every slide and fails on overflow |
| Deck | Body text at 13–15pt on a 960×540pt canvas | Nothing below 16pt; claims on slides, qualifications in notes |
| Harness | Session `PATH` appended the Copilot and Node *parent* directories, which on a Homebrew or npm-global install is the user's main bin directory — restoring ~1000 binaries by bare name and reducing "stubs first on PATH" to eight shadowed names | `PATH` is the stub directory plus the system default path; the two required executables are symlinked into the stub directory instead |
| Harness | `deniedPaths` omitted `~/.config/gh` — the GitHub CLI token store — in a talk about the GitHub agent, on a screen the presenter projects | 16 credential paths, including `.netrc`, `.git-credentials`, `.docker`, `.gnupg` |
| Harness | Ctrl-C on a live beat dumped a 15-line CPython traceback onto the projector | `KeyboardInterrupt` handled; signal exits normalised |
| Harness | Beat B's preconditions were checked *after* writing a session directory, stubs and a read/write policy; nothing ever removed them | Preconditions first; the session tree is removed if setup aborts |
| Harness | `gsutil`, `bq`, `helm`, `docker` and `cloud-sql-proxy` were neither stubbed nor denied | All stubbed and denied |
| Harness | No proxy variables reached the session, so login fails behind a corporate or conference proxy | Proxy and CA variables forwarded, and asserted in tests |
| Permissions | Deny lists used only `shell(x:*)`. GitHub documents that suffix as stem-plus-**space**, so a bare argument-less `gcloud` matched nothing and fell through to an ordinary prompt | Both `shell(x)` and `shell(x:*)` emitted for every blocked command |
| Sandbox policy | `userPolicy.readonlyPaths` / `readwritePaths` appear in no published schema; the only documentation nests them under `userPolicy.filesystem` | Both spellings emitted, neither asserted correct, and a verification row added. `/sandbox policy` is the only thing that settles it |
| Beat C | The deny and the stub targeted the same command, so a *working* deny produced no output — the audience could not distinguish enforcement from a model that quietly declined | Two probes of identical shape: `az --version` allowed as a positive control, `gcloud --version` denied |
| Fixture | The answer key said `contents: read` "remains" after adding a job-level permissions block. Job-level permissions **replace** the workflow-level block | Corrected, with the full block written out |
| Fixture | Actions pinned to Node 20 majors, removed from runners in 2026-09 | `checkout@v5`, `auth@v3`, `setup-terraform@v4` |
| Fixture | `${{ vars.GCP_PROJECT_ID }}` interpolated directly into a `run:` line | Moved into `env:` |
| Fixture | Beat A's answer stated unconditionally, but a fork PR cannot be granted `id-token: write` at all | Scoped to same-repo PRs; the fork case is now prepared Q&A |
| Tests | Flag and fixture assertions compared the launcher's output against the constants that produced it, so they could not fail | Literals declared in the test file; per-beat contract table |
| Tests | The credential test enumerated ten variable names; the harness's real guarantee is an allowlist | Exact key-set assertion, seeded with `TF_VAR_*`, `VAULT_TOKEN` and other decoys |
| Stagecraft | Three terminals, all blocked by interactive sessions, and no shell left to show the diff that Demo 2 builds toward | A second terminal for the diff, with its exact `--no-pager` command, in the runsheet |
| Stagecraft | "Confirm the baseline estate" at T-10, when Beat B refuses any rehearsed estate — so rehearsal poisons the stage run | T-10 starts by creating a new lab copy (pass 3 replaced the preflight script with commands) |
| Script | The payoff was spoken weaker than it was printed: the slide said "IAM is the wall", the script opened the climax with "Suppose" | The slide's own claim is now the spoken line |
| Script | No transitions between acts, and roughly one paragraph in three ended on a disclaimer already recorded in the ledger | Four spoken bridges; ledger sentences moved back to the ledger |

#### Added, because the argument was incomplete

**Prompt injection.** The talk claimed "the agent borrows your access" and never
said who gets to aim it. Beat A already hands the agent a `pull_request` CI log —
the textbook injection channel — so the fixture now carries a clearly labelled
planted instruction, and Demo 1 ends on the corollary: read-only is not a quiet
position, it is the input channel. Beat A has no shell, which makes the point
demonstrable rather than asserted.

**The unattended case.** Every control demonstrated needs a human at the terminal.
In CI, or with approvals pre-granted, the whole approval layer is gone and only
the tool list, the sandbox and the credential remain. That is now the bridge into
the closing argument, and it is what makes "IAM is the wall" land as a conclusion
rather than as one more control.

#### Refuted, so nobody re-fixes them

- **"The auth step is decorative."** A verifier ran the fixture: the Google
  provider resolves ADC at configure time, so `terraform plan` fails without
  credentials even though the config makes no API call. Beat A's causal story
  holds. An added `data "google_project"` block was reverted.
- **"The harness hedges away controls that work."** Three of the four controls
  said to be unstated were already documented in `demo/README.md`.
- **"`.gitignore` excludes the deck."** True of the original file, fixed before
  the verifier ran.

### Pass 1 — earlier

Established the core discipline: separate documented behaviour from locally
tested behaviour from unverified behaviour, and never let a single refusal stand
in for four different layers. It also introduced the defects pass 2 corrected —
mostly by hedging claims that were in fact documented, which cost the talk its
force without buying accuracy.

## Intentionally imperfect

The workflow still lacks its OIDC permission. The bucket still has the public IAM
member and none of the required hardening. The workflow still holds a federated
identity while running pull-request Terraform — named out loud from the stage
rather than quietly fixed, because it is the same borrowed-access story as the
agent's.

This repository does not implement a production plan/apply pipeline, WIF trust
policy, branch rules, or cloud IAM. Those are the delivery pattern, not a fourth
demo.
