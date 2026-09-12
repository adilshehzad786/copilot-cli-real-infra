# Talk runsheet

20 minutes plus Q&A. [TALK-SCRIPT.md](TALK-SCRIPT.md) has the narrative,
[demo/README.md](demo/README.md) has the exact prompts, and the deck's speaker
notes carry the same clock as the table below.

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

**If you are behind.** You will lose the time in Demo 2 — that is where it always
goes. If you leave Demo 2 after 12:00, cut in this order: slide 10 down to the
remote-MCP edge only; then slide 4 down to its gotcha line. Never cut Demo 3's
two probes, the home-directory line on slide 9, or the close.

## Before stage day

- [ ] `./scripts/check-lab.sh` — offline harness checks, not CLI evidence.
- [ ] Install Copilot CLI and record the exact version, OS and model in
      [docs/VERIFICATION.md](docs/VERIFICATION.md).
- [ ] Use a clean **macOS or Linux** VM with no cloud credentials, metadata
      identity, SSH agent, personal secrets or host-control socket.
- [ ] Rehearse all three beats on that CLI version. Resolve unsupported flags and
      settings warnings before recording anything.
- [ ] In every beat, inspect `/settings` Problems, `/sandbox status` and
      `/sandbox policy`. Confirm the synthetic `.env` is denied and tool network
      is off. On stage you only show the policy once, in Demo 3.
- [ ] Record whether Demo 2 actually shows a write prompt. A missing prompt is a
      finding to explain, not an invitation to fake one.
- [ ] Record Demo 3's two probes separately: the allowed `az --version` marker,
      and whatever the denied `gcloud --version` produces.
- [ ] **Record the three clips** `01-read`, `02-write`, `03-refuse`. Three
      recovery rows below depend on them and so does the entire no-network case.
      Without them the fallback is reading markdown aloud for nine minutes.
      No recordings ship with this repository.
- [ ] Play those clips with the laptop offline, at presentation font size.

## Ten minutes before

- [ ] **Create a new estate.** Rehearsal leaves the old one dirty and Demo 2 will
      refuse to launch on it.
      ```bash
      export DEMO_WORKSPACE="$(python3 scripts/setup-demo.py --parent ~/talk-lab)"
      printf 'export DEMO_WORKSPACE=%s\n' "$DEMO_WORKSPACE"
      ```
      Paste that second line into each terminal below.
- [ ] `./scripts/preflight.sh` — must print PASS for all three beats and report a
      clean estate.
- [ ] Terminal font 18–22pt minimum, ~100 columns, light on dark. Check it from
      the back of the room. `clear` before each beat.
- [ ] Disable notifications; hide unrelated terminals, shell history and account
      details.
- [ ] Open `presentations/copilot-cli-real-infra-deck.pptx` in the application you
      will actually present with. Check fonts and presenter notes.
- [ ] Keep [demo/prompts.txt](demo/prompts.txt) open to paste from. Do not retype
      prompts from the README, and do not project authentication commands.
- [ ] Confirm internet reaches the Copilot service. Blocked tool egress does not
      mean the CLI works offline.
- [ ] Ask someone for two photos and a 20-second clip. Start the timer.

## Stage setup — four terminals

Three beats each hold an interactive session, so the diff needs a shell of its
own. Open four terminals and paste the `DEMO_WORKSPACE` line into each.

```bash
# Terminal B — start FIRST, so it creates the branch before anything else runs
./demo/sessions/b-propose-change.sh
# Terminal A
./demo/sessions/a-read-only.sh
# Terminal C
./demo/sessions/c-refuse.sh
# Terminal R — leave at a shell prompt. This is where you show the diff.
```

Log in and inspect the policy in all three sessions off stage, then leave them
idle at their prompts. Present A, then B, then C. **Do not relaunch between
beats** — each launch creates a fresh configuration and may ask for login again.

Before each beat, `clear` that terminal and `cat "$DEMO_WORKSPACE/../banner-a.txt"`
(or `-b`, `-c`) so the exact flags are on screen while you narrate them.

After Demo 2's edit, in terminal R:

```bash
git -C "$DEMO_WORKSPACE" --no-pager diff -- terraform/main.tf
```

`--no-pager` matters: your personal `~/.gitconfig` still applies to this command,
and a configured pager on stage is a surprise you do not need.

To replay from baseline, create a **new** estate. Never reset the talk repository
or discard a session's work to recover a demo.

## Recovery

| Event | Action and narration |
|---|---|
| No CLI, unsupported setting, or sandbox off | Use the recordings. "This version hasn't passed the rehearsal checks." |
| No progress for 45 seconds | Switch to that beat's recording; otherwise show the prepared diff and label it as prepared |
| Session demands login on stage | Do not project it. Switch to the recording and say the session expired |
| Rate limit or quota error | Name it once, move to prepared material, keep the remaining beats. Do not retry on stage |
| No network to the model service | Announce it, run all three beats from recordings, keep slides 9–12 intact |
| Different diagnosis in Demo 1 | Compare it against the log on screen. Do not accept a confident answer without evidence |
| No write prompt in Demo 2 | Describe what happened. Do not claim every write always prompts |
| Model prints a diff in chat instead of editing | "Edit the file in place." Move on; do not debate it |
| Model edits an unexpected file | Show the whole diff, name what it touched, say you would reject this PR |
| Demo 2's session dies after editing | Do **not** relaunch — the clean-estate check refuses. Show the diff in terminal R and narrate from it |
| Model refuses with no tool call | "That is instruction following. We have not observed enforcement." |
| Approval prompt instead of a deny in Demo 3 | Decline it. A prompt is not enforcement evidence; say so and show the policy |
| Stub marker appears on the *denied* probe | The deny missed. Say so plainly — it is a better finding than the expected result |
| Sandbox bypass prompt | Decline and continue with the policy explanation. Do not relax policy to rescue a demo |
| Unexpected sensitive material | Stop projection and end the session |

## Status

The repository review is complete as a static and code review. Live product
rehearsal is still outstanding, because Copilot CLI was not run during that
review. Fill in [docs/VERIFICATION.md](docs/VERIFICATION.md) before presenting any
runtime behaviour as fact.
