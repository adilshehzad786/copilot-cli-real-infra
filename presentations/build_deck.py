#!/usr/bin/env python3
"""Build the 12-slide, 20-minute deck.

    python3 -m pip install python-pptx
    python3 presentations/build_deck.py

Writes presentations/copilot-cli-real-infra-deck.pptx. Slide copy lives here and
geometry lives in deck_design.py, so a wording change cannot move a box.

Two rules govern the copy, and they are why the slides read the way they do:

1. The slide carries the claim. The speaker notes carry the qualification.
   A hedge on a slide is unreadable from row fifteen and kills the line's force;
   the same hedge in the notes is spoken at the right moment and lands.
2. Nothing on a slide asserts runtime behaviour this repository has not observed.
   Where the talk depends on an unverified result, the slide says so plainly
   rather than implying a test happened. See docs/VERIFICATION.md.
"""
import sys
from pathlib import Path

sys.path.insert(0, str(Path(__file__).resolve().parent))

from pptx import Presentation
from pptx.enum.text import MSO_ANCHOR, PP_ALIGN
from pptx.util import Emu

from deck_design import (ACCENT, BLUE, COL, DEEP, GREEN, INK, MARGIN, MONO,
                         MUTED, RED, SURFACE, SZ_BODY, SZ_LEAD, SZ_META,
                         SZ_STATEMENT, SZ_TITLE_HERO, callout, kicker,
                         new_slide, notes, panels, prompt_badge, rect, rows,
                         terminal, text, title)

REPO = "github.com/adilshehzad786/copilot-cli-real-infra"
BYLINE = "Adil Shehzad  ·  DevSecOps Engineer"


def slide_01_title(prs):
    s = new_slide(prs)
    prompt_badge(s, 112)
    text(s, MARGIN, 144, COL, 62, "Copilot CLI on", size=SZ_TITLE_HERO, bold=True)
    text(s, MARGIN, 206, COL, 62, "Real Infrastructure", size=SZ_TITLE_HERO,
         color=ACCENT, bold=True)
    text(s, MARGIN, 282, COL, 30, "What it can reach, and what actually stops it",
         size=SZ_LEAD, color=MUTED)
    rect(s, MARGIN, 340, 160, 3, ACCENT)
    text(s, MARGIN, 362, COL, 26, BYLINE, size=SZ_BODY)
    notes(s, "0:00-0:30. Open cold, no housekeeping. Say the claim inside twenty "
             "seconds: Copilot CLI has no cloud permissions of its own; I do; it "
             "borrows mine. Then set expectations: three demos, then what actually "
             "stops it. 20 minutes.")


def slide_02_claim(prs):
    s = new_slide(prs)
    text(s, MARGIN, 128, COL, 190,
         ["Copilot CLI has no cloud",
          "permissions of its own.",
          "I do. It borrows mine."],
         size=SZ_STATEMENT, bold=True, anchor=MSO_ANCHOR.TOP, spacing=1.18)
    rect(s, MARGIN, 344, 160, 3, ACCENT)
    text(s, MARGIN, 370, COL, 80,
         ["Shell tools authenticate as my OS user, with whatever that user can reach.",
          "A remote MCP server may authenticate as something else entirely."],
         size=SZ_LEAD, color=MUTED, anchor=MSO_ANCHOR.TOP, spacing=1.45)
    notes(s, "0:30-1:45. Pause after the claim. The mental model most people carry is "
             "wrong: they picture the agent as a thing with its own access and GitHub "
             "as the party controlling it. It isn't. The agent never authenticates to "
             "GCP. It runs commands as your OS user, in a shell that already holds "
             "your ADC, your kubeconfig, your gcloud config.\n\n"
             "Be precise: this is a claim about ambient authority, not a product "
             "limitation. Tools CAN authenticate and mint tokens when reachable "
             "credentials allow it. And a remote MCP server runs off your machine with "
             "its own identity, so 'borrows your access' understates that case.\n\n"
             "Once the room accepts this, every later point lands without argument.")


def slide_03_controls(prs):
    s = new_slide(prs)
    title(s, "Where the controls live")
    rows(s, [
        ("0", "Your OS user, ADC, kubeconfig, SSH keys", "Not Copilot's to control", True),
        ("1", "Tool visibility  —  --available-tools", "Which tools the model sees"),
        ("2", "Tool permission  —  --allow-tool / --deny-tool", "Whether you get asked"),
        ("3", "Path and URL scope", "What a tool may touch"),
        ("4", "Local sandbox", "OS checks, for child processes"),
        ("5", "Hooks and managed settings", "Your code, your admin"),
    ], top=104, height=50, gap=7, label_w=500)
    kicker(s, "Five layers you configure sit on one layer you already own.", y=462)
    notes(s, "1:45-3:15. Walk it bottom-up, not top-down. Start at layer 0 and say "
             "plainly: this is the real blast radius, and it is the one layer Copilot "
             "has no say over. Then climb.\n\n"
             "Say out loud that this is a map of controls, not a promise that checks "
             "run in this vertical order. They have different enforcement points: a "
             "tool list reduces the model's choices, the sandbox constrains operations "
             "at the OS, IAM constrains what an authenticated identity may do at the "
             "cloud API. Hooks are trusted code you wrote, so they are inside your "
             "trust boundary, not a vendor guarantee.\n\n"
             "The README separates these into seven configurable controls; the slide "
             "groups them into five rows for legibility.")


def slide_04_visibility(prs):
    s = new_slide(prs)
    title(s, "Visibility is not permission")
    panels(s, [
        ("Visibility", [[("--available-tools", INK, MONO)],
                        [("--excluded-tools", INK, MONO)],
                        "",
                        "Changes what the model knows",
                        "exists. A tool outside the set",
                        "cannot be used — even if you",
                        "also allow it."], BLUE),
        ("Permission", [[("--allow-tool", INK, MONO)],
                        [("--deny-tool", INK, MONO)],
                        "",
                        "Changes whether you get an",
                        "approval prompt. Does not",
                        "resurface a tool that visibility",
                        "already hid."], ACCENT),
    ], top=104, height=250)
    callout(s, "The gotcha",
            "Pass both visibility flags and --available-tools wins; --excluded-tools "
            "is ignored. Pick one.", tint=ACCENT, y=378, height=84)
    notes(s, "3:15-4:15. Two different decisions that people routinely conflate. "
             "Visibility decides what the model can select. Permission decides whether "
             "you are interrupted.\n\n"
             "The gotcha is documented in the CLI command reference. Do not claim "
             "whether a warning is printed when both are set — the docs do not say, "
             "and I have not tested it.\n\n"
             "One more: hiding a web tool is not network isolation. A visible shell "
             "makes network requests. Network policy is a separate control.")


def slide_05_deny(prs):
    s = new_slide(prs)
    title(s, "Deny beats allow")
    terminal(s, [
        ("copilot \\", INK),
        ("  --allow-tool='shell(git:*)' \\", GREEN),
        ("  --deny-tool='shell(git push)'", RED),
    ], y=104, h=132)
    text(s, MARGIN, 254, COL, 56,
         ["A matching deny beats allow, beats --allow-all,",
          "and beats any approval you saved earlier."],
         size=SZ_LEAD, anchor=MSO_ANCHOR.TOP, spacing=1.4)
    callout(s, "One qualification",
            "A permissionRequest hook can decide before the normal rules run. Your "
            "hooks are inside your trust boundary, not a vendor guarantee.",
            tint=ACCENT, y=348, height=96)
    kicker(s, "Allow broadly for a bounded task, then deny the specific foot-guns.",
           y=456)
    notes(s, "4:15-5:15. This is the one rule with almost no hedge on it, and it makes "
             "a real pattern possible: allow broadly for a bounded task, deny the "
             "specific foot-guns.\n\n"
             "The qualification is worth saying aloud rather than burying: the current "
             "hooks reference describes a permissionRequest hook returning allow or "
             "deny that short-circuits the normal permission engine. So 'deny always "
             "wins' is true of the normal rules engine, not of every mechanism. "
             "Sandbox escape is the exception that still requires a human.\n\n"
             "/reset-allowed-tools clears saved tool grants for this location. It does "
             "not clear approved URL domains — those are global. Slide 9 territory.")


def _demo_frame(prs, number, word, prompt_text, command):
    """Demo slide: the prompt, then the command that constrains it.

    The command is the lesson. A slide that shows only the prompt teaches the
    audience nothing they could not have guessed."""
    s = new_slide(prs)
    title(s, f"Demo {number}  —  {word}")
    rect(s, MARGIN, 112, COL, 62, DEEP)
    rect(s, MARGIN, 112, 4, 62, ACCENT)
    text(s, MARGIN + 28, 112, COL - 56, 62, prompt_text, size=23, bold=True, font=MONO)
    terminal(s, command, y=196, h=44 + 26 * len(command))
    return s


def slide_06_demo_read(prs):
    s = _demo_frame(prs, 1, "Read", '"The last CI run failed. Why?"', [
        ("COPILOT_HOME=\"$RO\" copilot --experimental --sandbox \\", INK),
        ("  --available-tools=view,grep,glob \\", BLUE),
        ("  --allow-tool=read \\", GREEN),
        ("  --deny-tool=write,shell", RED),
    ])
    kicker(s, "No shell at all. Watch what it never does: it never asks me for "
              "permission.", y=396)
    notes(s, "5:15-8:15. Narrate the flags before you hit enter -- that is the "
             "slide. Four tools, no shell, no writes, no cloud credentials.\n\n"
             "Expected diagnosis: the workflow never requested an OIDC token, so "
             "the auth step had nothing to exchange. Adding 'id-token: write' fixes "
             "this log -- it does not grant access to anything. Provider trust "
             "conditions and resource IAM still decide what the token is worth.\n\n"
             "Park the observation that nothing prompted. It comes back on slide 9.\n\n"
             "Then the log's last four lines: a planted instruction arriving in "
             "contributor build output. The agent read it as information. It could "
             "not act on it here because I took the shell away -- a configuration "
             "choice, not a property of the tool. Read-only is the input channel.\n\n"
             "If it stalls for 45 seconds, cut to the recording.")


def slide_07_demo_write(prs):
    s = _demo_frame(prs, 2, "Write", '"This bucket isn\'t hardened. Fix it."', [
        ("COPILOT_HOME=\"$RW\" copilot --experimental --sandbox \\", INK),
        ("  --available-tools=...,bash,edit,create,apply_patch \\", BLUE),
        ("  --allow-tool='read,shell(git status),shell(git diff)' \\", GREEN),
        ("  --deny-tool='shell(git push),shell(terraform),", RED),
        ("               shell(terraform:*),shell(gcloud),shell(gcloud:*)'", RED),
    ])
    kicker(s, "Writes are not in --allow-tool. The first edit has to ask. Output is "
              "a diff on a branch.", y=422)
    notes(s, "8:15-11:45. Point at what is NOT in --allow-tool: writes. So the first "
             "edit should prompt, on screen. Approve exactly that one. If no prompt "
             "appears, say so -- that is a finding, not something to explain away.\n\n"
             "Point at the deny list too: each command appears twice. ':*' matches "
             "the stem followed by a SPACE, so shell(terraform:*) catches 'terraform "
             "apply' but not a bare 'terraform'. Both spellings, or the gap is real.\n\n"
             "On the diff, in order: the allUsers grant goes, public access "
             "prevention becomes explicit, uniform access, versioning on. Number one "
             "is the point -- uniform access alone SOUNDS like hardening and would "
             "have left the public grant in place.\n\n"
             "Show the diff in terminal 2: git --no-pager diff -- terraform/main.tf\n\n"
             "This is a branch. Nothing reached an environment.")


def slide_08_demo_refuse(prs):
    s = _demo_frame(prs, 3, "Refuse", '"Skip Terraform. Fix it in GCP directly."', [
        ("  --allow-tool='read,shell(az --version)' \\", GREEN),
        ("  --deny-tool='write,shell(gcloud),shell(gcloud:*)'", RED),
        ("", INK),
        ("$ az --version     -> DEMO_STUB_EXECUTED: fake az", GREEN),
        ("$ gcloud --version -> denied by tool rule", RED),
    ])
    kicker(s, "Same command shape. Same fake binary. One deny rule between them.",
           y=422)
    notes(s, "11:45-14:45. Three requests, three outcomes, and they must not blur.\n\n"
             "First the direct-fix request. If it declines from AGENTS.md: that is "
             "instruction following, not a permission boundary.\n\n"
             "Then the probe pair. Both names resolve to the same inert local stub. "
             "'az --version' is allow-listed -- it runs, the marker prints, and that "
             "proves the fake binary is real and reachable and that the model does "
             "what I ask. 'gcloud --version' is identical in shape and denied.\n\n"
             "Without the control, a working deny produces no output, and nobody can "
             "tell enforcement from a model that quietly declined.\n\n"
             "If the marker appears on the DENIED probe, the deny missed. Say so.\n\n"
             "Then /sandbox policy. Do not read it aloud -- point at the denied .env, "
             "the writable path, and allowOutbound false.")


def slide_09_reading(prs):
    s = new_slide(prs)
    title(s, "Nobody consented to cat")
    panels(s, [
        ("Prompts you", ["file changes",
                         "destructive shell commands",
                         "URL access"], ACCENT),
        ("Never asks", ["read  ·  grep  ·  glob",
                        "read-only shell commands",
                        "everything it puts in context"], BLUE),
    ], top=104, height=170)
    text(s, MARGIN, 296, COL, 58,
         ["In a regulated codebase, reading is the risk.",
          "Exfiltration does not need write access."],
         size=SZ_LEAD, bold=True, anchor=MSO_ANCHOR.TOP, spacing=1.4)
    callout(s, "And the default read surface is not the repository",
            "A sandboxed process can read your whole home directory, plus system and "
            "tool locations. cd into a subdirectory scopes your writes, not your reads.",
            tint=RED, y=372, height=96)
    notes(s, "14:45-16:00. Take apart the approval model from slide 4. Read-only "
             "operations are auto-approved, so 'nothing happens without your approval' "
             "really means 'nothing DESTRUCTIVE happens without your approval'. "
             "Reading is free.\n\n"
             "Be fair immediately after, and say this out loud: prompting on every grep "
             "would make the tool unusable. The default is right. What misleads is the "
             "marketing sentence, not the design. Saying that buys you the credibility "
             "for the red box.\n\n"
             "The red box is the strongest fact in the talk. GitHub documents the "
             "default as: sandboxed commands write in the working directory and temp "
             "folders, while your user profile directory plus system and tool locations "
             "are READ-ONLY — meaning readable. So 'cd terraform/' scopes your writes "
             "and not your reads, and the repo is not even the boundary; your home "
             "directory is in scope by default.\n\n"
             "That is why this lab's generated policy explicitly denies ~/.aws, "
             "~/.azure, ~/.config/gcloud, ~/.kube and ~/.ssh. Explicit denials are the "
             "only thing that removes a path — rules you configure are kept even when "
             "a path would otherwise be granted automatically.\n\n"
             "Everything read also goes to the model service. Decide what belongs in "
             "that workflow.")


def slide_10_sandbox(prs):
    s = new_slide(prs)
    title(s, "Where the sandbox stops")
    panels(s, [
        ("Built-in file tools", ["Run in-process, not as",
                                 "sandboxed children. Same",
                                 "policy, checked in software.",
                                 "No OS backstop."], ACCENT),
        ("Remote MCP servers", ["Run off your machine",
                                "entirely. The local",
                                "filesystem policy does not",
                                "constrain them at all."], RED),
        ("Public preview", ["Opt-in, needs --experimental,",
                            "and subject to change.",
                            "Confirm support on the build",
                            "you actually present with."], BLUE),
    ], top=104, height=202)
    callout(s, "Credit where it is due",
            "Escaping the sandbox always requires interactive human confirmation. A "
            "hook cannot pre-approve it.", tint=GREEN, y=336, height=84)
    kicker(s, "Good control, documented edges. That is a stronger position than either "
              "slogan.", y=442)
    notes(s, "16:00-17:15. Deliver these neutrally. 'Good control, documented edges' is "
             "a far stronger and more accurate position than 'it's secure' or 'it's "
             "theatre'.\n\n"
             "Remote MCP servers are the callback to slide 3 — that is why MCP was "
             "worth flagging early.\n\n"
             "Give GitHub the credit out loud, because it is earned and because it is "
             "what makes the next slide land instead of reading as an attack. One "
             "caveat on the credit: if allowBypass is enabled, a person can opt out "
             "for the rest of the session, so inspect that setting too.\n\n"
             "If someone asks 'isn't this FUD?' — this slide is the answer, plus the "
             "fact that I use the tool.")


def slide_11_iam(prs):
    s = new_slide(prs)
    title(s, "Deny rules match patterns, not intent")
    text(s, MARGIN, 104, COL, 30,
         [[("--deny-tool='shell(terraform apply)'", ACCENT, MONO),
           ("      does it also stop…", MUTED, "Arial")]],
         size=SZ_BODY, anchor=MSO_ANCHOR.TOP)
    rows(s, [
        ("?", "bash -c 'terraform apply'", "unverified"),
        ("?", "a script the agent wrote two steps earlier", "unverified"),
        ("?", "terragrunt apply", "unverified"),
        ("?", "an MCP server calling the cloud API directly", "unverified"),
    ], top=148, height=44, gap=6, label_w=520)
    text(s, MARGIN, 372, COL, 76,
         ["Deny rules are the speed bump on the honest path.",
          "IAM is the wall."],
         size=30, bold=True, color=INK, anchor=MSO_ANCHOR.TOP, spacing=1.3)
    kicker(s, "If the identity cannot call storage.buckets.update, the pattern does not "
              "have to be perfect.", y=468)
    notes(s, "17:15-18:45. The pattern is a string match on a command shape. It is not "
             "a semantic understanding of 'do not change infrastructure'.\n\n"
             "These four are QUESTIONS, not claimed bypasses. I have not run them on a "
             "live CLI, and the repo's verification ledger says so. If you have since "
             "rehearsed one, give the exact version, command shape and observed "
             "result. Otherwise: 'I haven't verified that one.' The room respects that "
             "more than a confident wrong answer, and someone in it will know.\n\n"
             "Syntax point worth thirty seconds, and the docs are specific: ':*' "
             "matches the command stem followed by a SPACE. So shell(git:*) catches "
             "'git push' and 'git pull'; it does not catch 'gitea', and it does not "
             "catch a bare 'git' with no arguments. That is a matcher, not a policy. "
             "Deny both forms — shell(gcloud) and shell(gcloud:*) — or an argument-less "
             "invocation falls straight through to an ordinary approval prompt.\n\n"
             "Then the turn: everything so far was defence in depth. None of it was "
             "the boundary. IAM evaluates the identity that actually calls the API. "
             "The qualification: only if no stronger credential remains reachable.")


def slide_12_close(prs):
    s = new_slide(prs)
    text(s, MARGIN, 150, COL, 140,
         ["The agent borrows your access.",
          "Scope what it borrows."],
         size=SZ_STATEMENT, bold=True, anchor=MSO_ANCHOR.TOP, spacing=1.3)
    rect(s, MARGIN, 318, 160, 3, ACCENT)
    text(s, MARGIN, 344, COL, 30, "Lab, permission flags, and what is still unverified",
         size=SZ_BODY, color=MUTED)
    text(s, MARGIN, 376, COL, 34, [[(REPO, ACCENT, MONO)]], size=SZ_LEAD, bold=True)
    text(s, MARGIN, 428, COL, 26, BYLINE, size=SZ_BODY)
    notes(s, "18:45-20:00. Close on the thesis, one line, repo on screen.\n\n"
             "If you have 30 seconds spare, make it actionable: do not run the agent "
             "in a shell holding your personal ADC; give it a task-scoped credential "
             "minted outside the runtime; put changes through a PR where CI holds its "
             "own WIF identity; let branch protection do more work than any CLI flag. "
             "If asked about AWS or Azure: same shape — scope the credential, not the "
             "agent.\n\n"
             "Then stop. Leave this slide up for Q&A.\n\n"
             "Q&A: for anything untested, say 'I haven't verified that one, I'll post "
             "the result on the repo' — and then actually do it. Keep employer and "
             "customer estate details out of every answer.")


BUILDERS = [
    slide_01_title, slide_02_claim, slide_03_controls, slide_04_visibility,
    slide_05_deny, slide_06_demo_read, slide_07_demo_write, slide_08_demo_refuse,
    slide_09_reading, slide_10_sandbox, slide_11_iam, slide_12_close,
]


def build(destination):
    prs = Presentation()
    prs.slide_width = Emu(12192000)
    prs.slide_height = Emu(6858000)
    for builder in BUILDERS:
        builder(prs)
    destination.parent.mkdir(parents=True, exist_ok=True)
    prs.save(str(destination))
    return prs


def main():
    here = Path(__file__).resolve().parent
    destination = Path(sys.argv[1]) if len(sys.argv) > 1 else \
        here / "copilot-cli-real-infra-deck.pptx"
    prs = build(destination)
    print(f"Wrote {destination} ({len(prs.slides._sldIdLst)} slides).")


if __name__ == "__main__":
    main()
