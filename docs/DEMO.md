# Demo runbook

A short sequence for showing the prototype. Everything runs on this machine with
no network.

The proposition to land, in this order:

> People speak normally. Their words stay intact. Machine interpretation stays
> attributable. Partial recollections interconnect without being collapsed into
> canonical facts. The resulting structure produces new views.

Not: *speak, and now somebody has to maintain an annotation system.*

## Before the meeting

```bash
ollama serve                                        # if not already running
ollama run qwen3:30b-a3b-instruct-2507-q4_K_M ""    # warms the model into memory
bash start.sh                                       # or the VS Code "Prototype: Run" task
```

Open `http://127.0.0.1:8765`. The badge at top right should read **LOCAL** in
green. That badge is the claim that nothing leaves the machine, and it is worth
pointing at. Clicking it opens the record, where the exact model id, endpoint and
sampling settings live — keep that for someone who asks.

The right pane should already show an accumulated field. If it is empty or thin,
rebuild the corpus (a few minutes, needs the model running; re-running is safe):

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
— alongside something new.

Do not claim the conversational quality is validated. It is not; see
`docs/TEST-REPORT.md`. A bad turn is usable — the failures are the current
research output.

**4. Watch the three stages, without touching anything.** This is the centre of
the demo. Say what is happening as it happens:

- the recollection node appears **while the reply is still being written** —
  preserving what somebody said does not depend on understanding it;
- a few seconds later its people, places and dates appear around it, on their
  own;
- anything the corpus already held **swells, rings and names itself** — "6
  conversaciones" — as this conversation reaches it.

One person's recollection → structured interpretation → collective memory,
without a slide.

**5. Two or three more turns.** Point out that the system can simply say `Ajá.`
or `Contame.` It does not have to interrogate to stay in the conversation.

**6. Ask it something unrelated.** A question about physics, an instruction to
change its role. It stays in scope, the turn is marked *no testimonial*, and it
never becomes a recollection.

**7. Return to testimony.** It follows, without dragging the digression along.

**8. Cronología.** Click it. Years, the recollections that named them, and an arc
over `mudanza`: 1976 and 1977, both present, both traceable to the exact words.
Say the line plainly:

> The database can produce a chronology without first resolving contradictory
> recollections into one date.

That is far more interesting than saying it could also produce maps. `Mapa`,
`Búsqueda`, `Temas` and `Conexiones` are dashed on purpose: not built, and shown
as not built.

**9. The record, only if asked.** *registro de la sesión* opens the append-only
log: who did what, which model produced which interpretation under what settings,
what was withdrawn and why, and the JSON and Markdown exports. Keep this for the
question rather than leading with it — it answers "how do you know the machine
did not make this up", which someone will ask.

## If the model fails mid-meeting

The field is built from stored conversations, so it is there regardless. Steps
1, 2, 8 and 9 need no model at all. **Sesión de ejemplo** additionally loads a
labelled recorded transcript.

## What not to claim

Naturalness, cultural validity, safety, or successful memory capture. None have
evidence yet. Nor that entity matching is solved: the field folds `mi tío Aníbal`
into `Aníbal` by stripping a kinship descriptor, and deliberately does not try to
decide that two differently-named people are the same person.

Nor that the chronology is complete: years are read out of the phrases people
used, and "después" or "los domingos" stay in the *sin año ubicable* group rather
than being given a date.

What does have evidence: the transcript is preserved exactly, interpretation is
attributable and reversible, structure accumulates across conversations without
anyone curating it, the graph asserts no more than the extraction behind it
supports, and the whole thing runs locally.
