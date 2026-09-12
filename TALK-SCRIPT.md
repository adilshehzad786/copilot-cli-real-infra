# Full talk script

The spoken argument, slide by slide. Twelve slides, twenty minutes, plus Q&A.
[README.md](README.md) holds the technical claims and sources;
[TALK-RUNSHEET.md](TALK-RUNSHEET.md) holds the clock and the recovery rules;
[docs/VERIFICATION.md](docs/VERIFICATION.md) holds what has and has not been
tested. Qualifications that belong in the ledger are not repeated on stage — a
speaker who hedges every third sentence trains the room to discount everything,
including the parts that are solid.

Stage directions are in brackets. Everything else is meant to be said.

---

## Act 1 — the claim

### Slide 1 — title, 0:00–0:30

[Open cold. No housekeeping, no thanks, no agenda slide.]

"Copilot CLI has no cloud permissions of its own. I do. It borrows mine.

"Everything worth knowing about running an agent on real infrastructure follows
from that. Three demos, then what actually stops it."

### Slide 2 — the claim, 0:30–1:45

"Most thinking about agent security starts from the wrong picture. People imagine
the agent as a thing that has access, and the vendor as the party controlling that
access. That is not what is happening.

"The agent never authenticates to my cloud. It runs shell commands as my OS user,
in a shell that is already holding my Application Default Credentials, my
kubeconfig, my gcloud config. When it runs `gcloud`, gcloud authenticates. When it
runs a client library, the library goes looking for credentials and finds mine.

"One exception worth holding onto, because it comes back later: a remote MCP
server runs off my machine entirely. That one may authenticate as a principal I
never see."

[Pause. Let the room re-sort the mental model.]

> **Bridge into Act 2.** "If it borrows my access, the interesting question is what
> I can put between the agent and the things that access reaches. There are seven
> answers, and they are not equally strong."

---

## Act 2 — where the controls live

### Slide 3 — the control map, 1:45–3:15

[Walk it bottom-up. Start at layer 0.]

"At the bottom is my OS user and the credentials it can already reach. That is the
real blast radius, and it is the one layer no Copilot setting touches.

"Above it: which tools the model can even see. Whether using one prompts me. Which
paths and URLs it may reach. The local sandbox, which is the only layer where the
operating system is doing the enforcing. And at the top, hooks and enterprise
managed settings.

"Read this as seven separate questions, not seven gates in a row. Nothing on this
slide checks the thing below it. They have different enforcement points, and one
of them — hooks — is code I wrote, which means it is inside my trust boundary
rather than a guarantee I was given."

### Slide 4 — visibility is not permission, 3:15–4:15

"These two get conflated constantly, and they do different jobs.

"`--available-tools` changes what the model knows exists. `--allow-tool` changes
whether I get interrupted. An allow rule cannot bring back a tool that visibility
already hid.

"The gotcha: pass both visibility flags and the allowlist wins — the denylist is
ignored. Pick one.

"And removing a web tool is not network isolation. A visible shell makes network
requests. That is a different control."

### Slide 5 — deny beats allow, 4:15–5:15

"Within the normal rules engine, a matching deny beats an allow, beats allow-all,
and beats an approval I saved last week. That makes a genuinely useful pattern
possible: allow broadly for a bounded task, then deny the specific foot-guns.

"One qualification I want to say out loud rather than bury. The hooks reference
describes a permission hook that can return a decision *before* those normal rules
run. So 'deny always wins' is a statement about the rules engine, not about every
mechanism in the product. My hooks are part of what I have to review."

> **Bridge into Act 3.** "That is the map. Now let us find out how much of it is
> real."

---

## Act 3 — the demonstrations

[Narrate the permissions, not the output. The room can read the terminal; what
they cannot see is why it was configured this way. `clear` and `cat` the banner
before each beat so the flags are on screen.]

### Slide 6 — demo 1, read, 5:15–8:15

"Four tools: view, grep, glob. Shell denied. Writes denied. No cloud credentials
anywhere near this session."

[Prompt from `demo/prompts.txt`.]

When the diagnosis lands:

"The workflow never asked for an OIDC token, so the auth step had nothing to
exchange. Adding `id-token: write` fixes this log. It does not give the job access
to anything — the provider trust conditions, the claim mapping and the resource
IAM all still have to be right. This takes us to the first failure, not to a
working pipeline.

"Now notice what did not happen. It read a workflow, a log, and a directory tree,
and it never once asked me for permission."

[Park that. It comes back on slide 9.]

Then, pointing at the log:

"One more thing about this file. Line three: event, pull request. A contributor's
branch produced this output, and part of what lands in a CI log is whatever the
build decided to print.

"Look at the bottom. That line is a planted instruction — go and grant the build
account owner. The agent read every line of this file and treated all of it as
information. It has no way to tell my diagnostic line from that one.

"So here is the half of the thesis I have to add. The agent borrows my access, and
whoever controls what it reads gets a vote on how that access gets spent. In this
session it could not have acted on it, because I took the shell away. That was a
configuration choice, not a property of the tool. Read-only is not a quiet
position. It is the input channel."

### Slide 7 — demo 2, write, 8:15–11:45

"This time editing tools are available, but writes are deliberately not
pre-approved. I want the first proposed change to stop and ask me."

[If a prompt appears, approve exactly that one write and point at it. If none
appears, say so and check saved grants — that is a finding, not a thing to
explain away. While it streams, narrate the four risks you expect rather than
watching in silence.]

Review the diff in terminal R, in this order:

1. The `allUsers` grant is gone.
2. Public access prevention is explicit.
3. Uniform bucket-level access removes reliance on object ACLs.
4. Versioning is on and `force_destroy` is off.

"Number one is the point. Uniform access on its own *sounds* like hardening and
would have left a public IAM grant sitting right there. A flag that sounds
reassuring is not the same as reviewing the access that remains.

"What I have is a branch and a diff. Nothing reached an environment. In the
pattern I would actually run, a person opens the pull request and CI applies with
its own identity — I have not built that pipeline here, because that is your IAM
and your branch rules, not something anyone can ship in a demo repo."

### Slide 8 — demo 3, refuse, 11:45–14:45

"First, let me just ask for the thing outright."

[The direct-fix request. If it declines:]

"It declined. That is instruction following — it read the repository's rules and
complied. It is not a permission boundary, and I have not shown you one yet.

"So let us actually test one. Two commands. Same shape, same fake binary behind
them — every cloud command name in this session points at a harmless local stub
that cannot touch a cloud. One difference: a deny rule."

[Probe 1: `az --version`. The marker prints.]

"That is the control. The fake binary is real, it is reachable, and the model will
run what I ask."

[Probe 2: `gcloud --version`.]

"Same shape. Denied before it got there.

"Three outcomes and they are not interchangeable: a tool-rule denial, a model
declining with no tool call at all, and execution reaching the harness. Only the
first one is enforcement."

[Then `/sandbox policy`. Do not read it aloud — point at three things.]

"Resolved policy for this directory. Denied `.env`. The work directory.
`allowOutbound: false`. If sandboxing were off, this screen would say so."

> **Bridge into Act 4.** "Three demos, three different outcomes — and not one of
> them proved the thing people usually assume it proved. So let us talk about what
> I still cannot see."

---

## Act 4 — the honest limits

### Slide 9 — reading is the risk, 14:45–16:00

"Back to slide 4. Read-only operations are auto-approved. So 'nothing happens
without your approval' actually means 'nothing *destructive* happens without your
approval.' Reading is free.

"To be fair — and I mean this — prompting on every grep would make the tool
unusable. The default is right. What misleads is the marketing sentence, not the
design.

"But in a regulated codebase, reading is the risk. Exfiltration does not need
write access.

"And the default read surface is not what people assume. It is not the repository.
GitHub documents it: a sandboxed process can read your whole home directory, plus
system and tool locations. So `cd terraform/` scopes your writes and does nothing
to your reads — the repo was never the boundary in the first place.

"Explicit denials are the only thing that removes a path. That is why this lab's
policy names `~/.aws`, `~/.config/gcloud`, `~/.config/gh`, `~/.kube` and `~/.ssh`
by absolute path. And note what that is: me enumerating what I happened to think
of."

### Slide 10 — where the sandbox stops, 16:00–17:15

"Three documented edges. The built-in file tools run in-process — same policy,
checked in software, no OS backstop. Remote MCP servers run off my machine, and
the filesystem policy does not constrain them at all; that is the callback to
slide 3. And the whole feature is public preview.

"Credit where it is due, because it is earned: escaping the sandbox always
requires a human saying yes. A hook cannot pre-approve it. That is a good design
decision and I want to be the person who says so.

"Good control, documented edges. That is a stronger and more accurate position
than either 'it's secure' or 'it's theatre.'"

### Slide 11 — patterns, not intent, 17:15–18:45

"A deny rule matches a command shape. It is a string pattern. It is not a semantic
understanding of 'do not change infrastructure.'

"The docs are specific about the matcher: colon-star matches the stem followed by
a space. `shell(git:*)` catches `git push` and `git pull`. It does not catch
`gitea`, and it does not catch a bare `git`. That is a matcher, not a policy.

"So: does a rule on `terraform apply` also stop `bash -c 'terraform apply'`? A
script the agent wrote two steps earlier and then ran? `terragrunt apply`? An MCP
server that calls the cloud API and never touches my shell?

"I have not verified those on this version, and the repo says so rather than
guessing. If you know, find me afterwards — I would rather publish your answer
than my assumption."

[Then the turn — this is the payoff. Slow down.]

"One thing I have quietly assumed for eighteen minutes: every control I have shown
you had me sitting in front of it. The approval prompt needs a person. The sandbox
bypass needs a person. The deny rule is the only one on that list that works while
you are asleep.

"The moment this runs in CI, or with approvals pre-granted so it stops
interrupting you, the whole approval layer is gone. What is left is the tool list,
the sandbox, and the credential.

"Everything in act two is a speed bump on the honest path. A deny rule stops the
command it recognises. A sandbox stops the child process it wraps. Both assume the
agent is doing roughly what I asked.

"IAM is the wall. If the only credential in that runtime cannot write to that
bucket, it does not matter which spelling the model picked, whether my pattern
matched it, or whether it wrote a script instead. The API says no.

"The limit on that: IAM for one service account does not protect a personal
credential file sitting next to it. Scope the credential, and keep the stronger
one out of the room."

---

## Act 5 — close

### Slide 12 — close, 18:45–20:00

"So the honest version of the thesis is this. The controls in act two reduce
accidents. The credential decides the worst case.

"If you do one thing on Monday: do not run this in a shell that is holding your
personal ADC. Give it a task-scoped credential minted outside the runtime, put
changes through a pull request where CI holds its own identity, and let branch
protection do more work than any CLI flag. AWS and Azure differ in mechanism and
not in shape — scope the credential, not the agent.

"The lab, the permission flags, and an honest list of what I have not verified are
all in the repo.

"The agent borrows your access. Scope what it borrows."

[Stop. Leave the slide up.]

---

## Q&A

**"Isn't this just FUD?"**
"I use the tool, and I gave it credit twice — the sandbox-escape design is good and
the auto-approve default is right. I am mapping the boundary, not arguing against
the product."

**"Why not just use `--yolo` in a container?"**
"Reasonable, and a disposable container is a legitimate place for broad
permissions. The failure mode is the alias. The moment `--yolo` becomes muscle
memory it follows you into a repo that has credentials in it."

**"Your deny rule only blocks names you thought of."**
"Correct, and that is the argument. That is why the last slide is about the
credential and not about the pattern."

**"You said read-only is the input channel — so is any agent reading untrusted
content unsafe?"**
"Unsafe is the wrong axis. It means the read surface is an attack surface, so treat
what the agent reads with the same care as what it can run. In practice: do not
point it at fork build output while it holds anything worth spending."

**"How do I audit what one of these sessions actually did?"**
"Honestly, that is the weakest part of my own setup. I have the transcript and the
shell history, and that is not an audit trail. If you have solved it I want to
hear how."

**Anything untested:** "I haven't verified that one. I'll put the result in the
repo." Then actually do it — that follow-up is free content and people remember it.

**About work:** regulated fintech on GCP, in general terms. No estate details, no
customer names, no architecture specifics.
