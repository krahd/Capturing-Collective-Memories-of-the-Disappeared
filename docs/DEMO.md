# Demo runbook

A short sequence for showing the prototype. Everything runs on this machine with
no network.

The proposition to land, in this order:

> Speak normally. The conversation is preserved exactly. Structure emerges from
> many conversations. That structure can then be explored and used.

Not: *speak, and now somebody has to maintain an annotation system.*

## Before the meeting

```bash
ollama serve                                        # if not already running
ollama run qwen3:30b-a3b-instruct-2507-q4_K_M ""    # warms the model into memory
bash start.sh                                       # or the VS Code "Prototype: Run" task
```

Open `http://127.0.0.1:8765`. The badge at top right should read
`qwen3:30b-a3b-instruct-2507-q4_K_M · local` in green — that badge is the claim
that nothing leaves the machine, and it is worth pointing at.

The right pane should already show an accumulated field. If it is empty or thin,
rebuild the corpus (takes a few minutes, needs the model running):

```bash
python scripts/build_demo_corpus.py
```

The first reply after starting is slow while the model loads. Warm it first.

## Sequence

**1. Start from the field, not the conversation.** Before typing anything, let
the right pane sit there: several conversations, each a small cluster, with a few
larger ringed nodes sitting *between* clusters. Those are the people and places
more than one conversation reached.

**2. Click a shared node** — `el Cerro` is usually the densest. It shows how many
conversations it appears in, then the exact sentences, in each speaker's own
words, that produced it. Nothing was tagged to make that happen.

**3. Now talk.** New conversation, then speak in Uruguayan Spanish. Mention
someone or somewhere the corpus already knows — Aníbal, Julio, el Cerro, La Teja
— alongside new material.

Do not claim the conversational quality is validated. It is not; see
`docs/TEST-REPORT.md`. A bad turn is usable — the failures are the current
research output.

**4. Watch the field grow, without touching it.** A few seconds after the reply,
the new recollection appears and attaches. If you named something the corpus
already held, that node grows and its conversation count goes up. Say plainly
that no one selected, tagged or approved anything.

**5. Plurality.** Two conversations in the corpus date the same move differently
— one says 76, the other 77. Both are in the field; neither was resolved away.
This is the point worth dwelling on: the structure is computationally addressable
*and* it preserves disagreement.

**6. What it could produce.** The **Puede producir** strip — timeline, map,
search, themes, connections. Say clearly that these are not built. They are there
to show that the material supports them.

**7. The record, only if asked.** *registro de la sesión* opens the append-only
log: who did what, which model produced which interpretation, under what sampling
settings, what was withdrawn and why. Keep this for the question rather than
leading with it — it answers "how do you know the machine did not make this up",
which someone will ask.

**8. Export.** **Markdown** — transcript, attributions, withdrawals and record,
readable without this application.

## If the model fails mid-meeting

The field is built from stored conversations, so it is there regardless. Steps
1, 2, 5, 6 and 8 need no model at all. **Sesión de ejemplo** additionally loads a
labelled recorded transcript.

## What not to claim

Naturalness, cultural validity, safety, or successful memory capture. None have
evidence yet. Nor that entity matching is solved: the field folds `mi tío Aníbal`
into `Aníbal` by stripping a kinship descriptor, and deliberately does not try to
decide that two differently-named people are the same person.

What does have evidence: the transcript is preserved exactly, interpretation is
attributable and reversible, structure accumulates across conversations without
anyone curating it, and the whole thing runs locally.
