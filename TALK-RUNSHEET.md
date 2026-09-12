# Talk runsheet

20 minutes plus Q&A. [TALK-SCRIPT.md](TALK-SCRIPT.md) has the narrative,
[docs/lab-guide.md](docs/lab-guide.md) has every command, and
[docs/prompts.txt](docs/prompts.txt) is what you paste.

## Clock

| Clock | Slide | Segment | Exit condition |
|---|---|---|---|
| 00:00–00:30 | 1 | Title | The claim is already said |
| 00:30–01:45 | 2 | The claim | The room separates the model from the tools around it |
| 01:45–03:15 | 3 | Where the controls live | Layer 0 is understood as the real blast radius |
| 03:15–04:15 | 4 | Visibility is not permission | Two different decisions, not one |
| 04:15–05:15 | 5 | Deny beats allow | Deny precedence, and the hook qualification |
| 05:15–08:15 | 6 | **Demo 1 — read** | Missing OIDC permission diagnosed; nothing prompted |
| 08:15–11:45 | 7 | **Demo 2 — write** | Approval shown, branch and diff reviewed |
| 11:45–14:45 | 8 | **Demo 3 — refuse** | Allowed probe vs denied probe; policy on screen |
| 14:45–16:00 | 9 | Reading is the risk | Disclosure separated from modification |
| 16:00–17:15 | 10 | Where the sandbox stops | Three edges, plus the credit |
| 17:15–18:45 | 11 | Patterns, not intent | IAM named as the actual boundary |
| 18:45–20:00 | 12 | Close | Thesis, repo, stop |

**If you are behind.** You will lose the time in Demo 2. If you leave it after
12:00, cut slide 10 to the remote-MCP edge only, then slide 4 to its gotcha line.
Never cut Demo 3's two probes, the home-directory line on slide 9, or the close.

## Before stage day

- [ ] Install Copilot CLI and record the exact version, OS and model in
      [docs/VERIFICATION.md](docs/VERIFICATION.md).
- [ ] Use a clean **macOS or Linux** VM with no cloud credentials, no metadata
      identity, no SSH agent, no host-control socket.
- [ ] Walk [docs/lab-guide.md](docs/lab-guide.md) end to end on that CLI version.
      Resolve unsupported flags and `/settings` Problems warnings before recording.
- [ ] In every beat check `/sandbox status` and `/sandbox policy`. Confirm `.env`
      is denied and tool network is off. On stage you show the policy once, in
      Demo 3.
- [ ] Record whether Demo 2 actually shows a write prompt. A missing prompt is a
      finding to explain, not an invitation to fake one.
- [ ] Record Demo 3's probes separately: the allowed `az --version` marker, and
      whatever the denied `gcloud --version` produces.
- [ ] **Record three clips** `01-read`, `02-write`, `03-refuse`. Four recovery
      rows and the whole no-network case depend on them. None ship with this repo.
- [ ] Play them back offline, at presentation font size.

## Ten minutes before

- [ ] **Build a fresh lab copy.** Rehearsal leaves edits on a branch.
      ```bash
      rm -rf ~/copilot-lab
      cp -R lab ~/copilot-lab && cd ~/copilot-lab
      git init -q && git add -A && git commit -qm "lab baseline"
      echo 'DEMO_SENTINEL=synthetic-not-a-secret' > .env
      export PATH="$PWD/stubs:$PATH"
      export RO="$(mktemp -d)" RW="$(mktemp -d)"
      sed "s|__LAB__|$PWD|g; s|__HOME__|$HOME|g" policy/read-only.json  > "$RO/settings.json"
      sed "s|__LAB__|$PWD|g; s|__HOME__|$HOME|g" policy/read-write.json > "$RW/settings.json"
      ```
- [ ] Log in once in each config directory, off stage:
      `COPILOT_HOME="$RO" copilot` then `/login`, `/exit`. Repeat for `$RW`.
      **Do not do this on stage** — a login prompt mid-demo costs you the beat.
- [ ] Confirm the stubs answer: `gcloud --version` and `az --version` both print
      `DEMO_STUB_EXECUTED`.
- [ ] Terminal font 18–22pt, ~100 columns, light on dark. Check it from the back
      of the room. `clear` before each beat.
- [ ] Disable notifications; hide unrelated terminals, shell history, account
      details.
- [ ] Open `presentations/copilot-cli-real-infra-deck.pptx` in the application you
      will actually present with. Check fonts and presenter notes.
- [ ] Keep [docs/prompts.txt](docs/prompts.txt) open to paste from.
- [ ] Confirm internet reaches the Copilot service. Blocked tool egress does not
      mean the CLI works offline.
- [ ] Ask someone for two photos and a 20-second clip. Start the timer.

## Two terminals

One terminal runs the beats. A second stays at a shell prompt for the Demo 2 diff —
the beat terminal is blocked by an interactive session when you need it.

Export `RO`, `RW` and `PATH` in **both**, and `cd ~/copilot-lab` in both.

Each beat is one command from [docs/lab-guide.md](docs/lab-guide.md). Type it, or
paste it — but let the room see the flags before you hit enter. That is the slide.

After Demo 2's edit, in terminal 2:

```bash
git --no-pager diff -- terraform/main.tf
```

## Recovery

| Event | Action and narration |
|---|---|
| No CLI, unsupported flag, or sandbox off | Use the recordings. "This version hasn't passed the rehearsal checks." |
| No progress for 45 seconds | Switch to that beat's recording; otherwise show the prepared diff and label it |
| Session demands login on stage | Do not project it. Switch to the recording and say the session expired |
| Rate limit or quota error | Name it once, move to prepared material, keep the remaining beats |
| No network to the model service | Announce it, run all three beats from recordings, keep slides 9–12 intact |
| `zsh: missing delimiter` or `syntax error near (` | You lost a quote. `--deny-tool='...'` — quote from the equals sign |
| Different diagnosis in Demo 1 | Compare it against the log on screen. Do not accept a confident answer without evidence |
| No write prompt in Demo 2 | Describe what happened. Do not claim every write always prompts |
| Model prints a diff in chat instead of editing | "Edit the file in place." Move on; do not debate it |
| Model edits an unexpected file | Show the whole diff, name what it touched, say you would reject this PR |
| Demo 2's session dies after editing | The edits are on disk. Show the diff in terminal 2 and narrate from it |
| Model refuses with no tool call | "That is instruction following. We have not observed enforcement." |
| Approval prompt instead of a deny in Demo 3 | Decline it. A prompt is not enforcement evidence; say so and show the policy |
| Stub marker appears on the *denied* probe | The deny missed. Say so plainly — a better finding than the expected result |
| Sandbox bypass prompt | Decline and continue with the policy explanation. Do not relax policy to rescue a demo |
| Unexpected sensitive material | Stop projection and end the session |

## Status

Copilot CLI was not run during the review that produced this repository. Fill in
[docs/VERIFICATION.md](docs/VERIFICATION.md) from your own rehearsal before
presenting any runtime behaviour as fact.
