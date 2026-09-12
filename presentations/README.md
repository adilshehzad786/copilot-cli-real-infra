# Presentation

[copilot-cli-real-infra-deck.pptx](copilot-cli-real-infra-deck.pptx) is the deck:
**12 slides, 20 minutes**, with speaker notes carrying the same clock as
[TALK-RUNSHEET.md](../TALK-RUNSHEET.md) and the same beats as
[TALK-SCRIPT.md](../TALK-SCRIPT.md).

This is the only deck to present. `archive/deck-v1-original-do-not-present.pptx`
is the pre-review 18-slide version, kept for provenance. It still carries claims
the review corrected — "six layers", an unqualified "deny always wins", a
`roles/viewer` recipe, and a placeholder repository URL. Do not open it on stage.

## Slide map

| Slide | Beat | Clock |
|---|---|---|
| 1 | Title | 0:00–0:30 |
| 2 | The claim: it borrows your access | 0:30–1:45 |
| 3 | Where the controls live | 1:45–3:15 |
| 4 | Visibility is not permission | 3:15–4:15 |
| 5 | Deny beats allow | 4:15–5:15 |
| 6 | **Demo 1 — read** | 5:15–8:15 |
| 7 | **Demo 2 — write** | 8:15–11:45 |
| 8 | **Demo 3 — refuse** | 11:45–14:45 |
| 9 | Reading is the risk | 14:45–16:00 |
| 10 | Where the sandbox stops | 16:00–17:15 |
| 11 | Patterns, not intent → IAM is the wall | 17:15–18:45 |
| 12 | Close | 18:45–20:00 |

Nine and a half of the twenty minutes are live demo, which is the part people
remember and the part worth protecting when you run behind.

## Rebuilding

The deck is generated, not hand-edited. Three files:

| File | Job |
|---|---|
| `deck_design.py` | Palette, type scale and layout primitives. Geometry only. |
| `build_deck.py` | Slide copy and speaker notes, one function per slide. |
| `preview.py` | Renders each slide to PNG and fails on text that overflows its box. |

```bash
python3 -m pip install python-pptx pillow
python3 presentations/build_deck.py     # writes copilot-cli-real-infra-deck.pptx
python3 presentations/preview.py        # writes previews/, reports overflow
```

`preview.py` reads the generated `.pptx` rather than the content module, so it
checks what is actually in the file you will present. It is a legibility check,
not a faithful PowerPoint renderer — it exists to catch a line that runs past its
box and a slide too dense to read from the back of a room. It exits non-zero if
anything overflows.

Editing the `.pptx` directly works, but the next build overwrites it. Change the
copy in `build_deck.py` instead.

The earlier revision was authored as a JSON source for `@oai/artifact-tool`, which
is only available inside the OpenAI Codex runtime — meaning the deck could not be
rebuilt by the person who owns it. That toolchain has been removed in favour of
`python-pptx`, which installs anywhere.

## Two rules the copy follows

1. **The slide carries the claim; the notes carry the qualification.** A hedge on
   a slide is unreadable from row fifteen and drains the line of force. The same
   hedge in the speaker notes gets spoken at the right moment and lands. This is
   why the slides read more confidently than the previous revision while saying
   nothing less accurate.
2. **No slide asserts runtime behaviour this repository has not observed.** Slide
   11 prints "unverified" against the four alternate-execution questions on
   purpose. Change that only from evidence recorded in
   [docs/VERIFICATION.md](../docs/VERIFICATION.md).

## Design

GitHub dark, 960×540pt (13.33×7.5in, 16:9). Arial for text, Courier New for
anything a terminal would print. Nothing in the slide body is below 16pt — the
previous deck used 13–15pt, which is roughly 26px on a 1080p projector and
unreadable past the middle of a room.

Palette: canvas `#0D1117`, surface `#161B22`, ink `#E6EDF3`, muted `#8B949E`,
accent `#F0883E`, with `#3FB950` / `#58A6FF` / `#F85149` for allowed, neutral and
denied states in the terminal blocks.
