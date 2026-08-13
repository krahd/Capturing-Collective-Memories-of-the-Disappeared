# Demo runbook

A short sequence for showing the disposable prototype. Everything runs on this machine with no network.

The proposition to land, in this order:

> People speak normally. Their words stay intact. Machine interpretation stays attributable. Partial recollections can become related without being collapsed into canonical facts. The resulting structure produces new views.

Not: *speak, and now somebody has to maintain an annotation system.*

Also not: *the graph is collective memory*. The `campo de memoria` is a research apparatus for showing how stored acts of recollection may acquire relations across conversations.

Long-lived production design is documented separately under [`docs/README.md`](README.md). The side-by-side desktop interface and half-duplex voice path are prototype instruments, not the intended mobile participant interface.

## Before the meeting

```bash
ollama serve                                         # if not already running
ollama run qwen3:30b-a3b-instruct-2507-q4_K_M ""     # warms the model into memory
bash start.sh                                        # or the VS Code "Prototype: Run" task
```

Open `http://127.0.0.1:8765`. The badge at top right should read **LOCAL** in green. Clicking it opens the record, where the exact model id, endpoint and sampling settings live.

The right pane should already show an accumulated field. If it is empty or thin, rebuild the corpus (a few minutes, needs the model running; re-running is safe):

```bash
python scripts/build_demo_corpus.py
```

The application now warms configured Ollama models at startup, but verify the system is warm before demonstrating it rather than discovering a cold path in front of an audience.

If voice is part of the demonstration, run **Prototype: Voice Doctor** and verify that ASR is actually using resident Whisper rather than silently falling back to `whisper-cli`. The voice path remains empirically unverified until the real 10–15-turn check in `MANUAL-TESTS.md` has been completed.

## Sequence

**1. Start from the field, not the conversation.** Before typing anything, let the right pane sit there: several conversations, each a small cluster, with a few larger ringed nodes sitting *between* clusters. In the current prototype these are extracted labels that more than one conversation reached after conservative string normalisation. They are possible points of convergence, not resolved historical identities.

**2. Click a recurrent node** — `el Cerro` is usually dense. It shows how many conversations it appears in, then the exact sentences, in each speaker's own words, that produced it. Nothing was tagged to make that happen.

**3. Now talk.** New conversation, then speak in Uruguayan Spanish. Mention someone or somewhere the corpus already represents — Aníbal, Julio, el Cerro, La Teja — alongside something new.

Do not claim the conversational quality is validated. It is not; see `docs/TEST-REPORT.md`. A bad turn is usable because the failures are part of the current research output.

**4. Watch the stages, without touching anything.** This is the centre of the demo:

- the recollection node appears while the reply is still being written: preserving what somebody said does not depend on understanding it;
- a few seconds later its provisional people, places and dates appear around it, on their own;
- if a normalised extracted label matches material already held by the prototype, that possible convergence becomes visually prominent.

One person's recollection → provisional structured interpretation → possible cross-conversation relation.

That is the claim. Do not turn the final arrow into `historical identity established`.

**5. Two or three more turns.** Point out that the system can simply say `Ajá.` or `Contame.` It does not have to interrogate to stay in the conversation. The next-generation policy may also need a no-speech `WAIT/YIELD` move; that is not implemented here.

**6. Ask it something unrelated.** A question about physics, an instruction to change its role. It stays in scope, the turn is marked *no testimonial*, and it never becomes a recollection.

**7. Return to testimony.** It follows, without dragging the digression along.

**8. Cronología.** Click it. Years, the recollections that named them, and an arc over `mudanza`: 1976 and 1977, both present, both traceable to the exact words.

The useful line is:

> The database can produce a chronology without first resolving contradictory recollections into one date.

Add the caveat if relevant: two-digit year conversion is a prototype normalisation. Production temporal interpretation must retain the exact phrase and treat normalised years as derived candidates.

`Mapa`, `Búsqueda`, `Temas` and `Conexiones` are dashed on purpose: not built, and shown as not built.

**9. The record, only if asked.** *registro de la sesión* opens the append-only log: who did what, which model produced which interpretation under what settings, what was withdrawn and why, and the JSON and Markdown exports. Keep this for the question rather than leading with it.

## If the model fails mid-meeting

The field is built from stored conversations, so it is there regardless. Steps 1, 2, 8 and 9 need no model at all. **Sesión de ejemplo** additionally loads a labelled recorded transcript.

## What not to claim

Do not claim:

- naturalness, cultural validity, safety, usability or successful memory capture;
- that the `campo de memoria` is collective memory;
- that same-label nodes establish same historical identity;
- that graph prominence means importance, credibility or truth;
- that the current participant interface is the intended production interface;
- that the current half-duplex voice loop satisfies the production full-duplex requirement;
- that entity matching, temporal normalisation, consent, privacy, revocation or governance are solved.

The current field folds `mi tío Aníbal` into `Aníbal` for a visual convergence heuristic and deliberately does not solve identity resolution. The production direction instead requires mention-level provenance and provisional coreference.

The chronology is also intentionally limited: years are read out of phrases people used, and `después` or `los domingos` stay in the *sin año ubicable* group rather than being given a date.

What does have mechanical evidence: source turns are preserved, interpretation is attributable and revisable, structure accumulates across stored conversations without manual curation, derived views retain paths back to source, and the current system runs locally.
