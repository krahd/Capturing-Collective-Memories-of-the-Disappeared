# Capturing Collective Memories of the Disappeared

This repository is the dedicated implementation space for **Capturing Collective Memories of the Disappeared with Artificial Intelligence**, a research project on conversational interfaces for eliciting and preserving dispersed, partial and situated memories connected to Uruguay's detained-disappeared.

It is a different project from `desaparecidos.uy`, the computational memorial artwork.

## Current phase

The current code is intentionally a **disposable interaction prototype**. Its purpose is to make the conversational interaction and the apparatus for working on a conversation concrete enough to test. The prototype is not the architecture of the eventual research system and does not need to survive into it.

The current goal is defined in `GOAL.md`; interaction rationale and non-goals are in `PROTOTYPE.md`.

## What the prototype does

It has two coordinated views:

- **Conversation**: participant-led text conversation, driven by a compact policy for natural Uruguayan Spanish, non-leading follow-up, digression, uncertainty, correction and refusal.
- **Campo de memoria**: the structure that many conversations accumulate into, drawn as one graph and grown automatically as people speak.

The raw transcript is never silently rewritten when derived material changes.

### The memory field

The right-hand pane is not a workbench and has no annotation controls. Extraction
runs by itself behind each testimony turn, so the structure is a by-product of
speaking rather than a curation task. Nothing is selected, tagged or approved.

Its shape encodes a claim. A conventional knowledge graph reads
`Person → Event → Place` and thereby presents testimony as resolved fact. Here
**recollections are first-class nodes**:

```text
Conversación 07
    ├── recuerdo r1 ── menciona ───────→ Julio
    │                └─ menciona lugar ─→ la facultad
    └── recuerdo r2 ── menciona fecha ──→ 1976
```

Every edge says `menciona`. That weakness is deliberate: extraction establishes
that a recollection *referred to* something, not that the remembered episode
occurred there or happened then. For the same reason a node is drawn as a person
only when extraction explicitly said `person`; what it could only call an entity
stays a generic entity, because an institution or an object silently labelled a
person is a claim nobody made.

Entities are shared across conversations, so separate accounts meet at the same
node and the graph densifies as more people speak. Nodes several conversations
reach are drawn larger and ringed. Two recollections may date the same event
differently; both edges are kept and nothing resolves them into a canonical
value. Uncertainty, hearsay and correction mark the recollection that carries
them rather than becoming entities of their own, because they describe how
something was said, not a thing in the world.

Clicking any node shows the exact words it came from, across every conversation
that produced it. That is the only inspection affordance, and it reads as
exploration rather than labour.

### Growth happens in visible stages

The field is not updated once, some seconds later. Three things happen and each
is meant to be seen separately, because together they *are* the explanation of
what the system does:

1. **The words are preserved.** The recollection node appears as soon as the turn
   is stored — before the reply has been composed. Preserving what somebody said
   does not depend on understanding it.
2. **Interpretation arrives.** People, places, dates and themes read out of that
   recollection appear around it, on their own, once the conversational model is
   free.
3. **The collective connection is made.** If any of them already existed
   elsewhere, the edge attaches to the existing node and that node swells and
   pulses, named, with the number of conversations that now reach it.

No caption explains the pipeline. The animation is the explanation.

### What the material can produce

Below the graph, **Extraído** counts what exists and **Puede producir** names
what the material could support.

**Cronología** is built. Years are read out of the phrases people actually used —
"el 76", "por el 77, 78, por ahí" — and each year holds the recollections that
named it. A subject dated more than one way sits at both years, joined by an arc,
with both source recollections reachable; the view says plainly that it does not
resolve the difference. Time material that names no locatable year — "después",
"los domingos" — is kept and shown as such rather than dropped or given an
invented date. The point is not that a chronology can be drawn. It is that one
can be drawn without first deciding which recollection has the date right.

Map, search, themes and connections are deliberately not built, and are marked as
such.

Control and off-topic turns never become recollections, and withdrawn
interpretation leaves the field while remaining in the transcript and the record.

### Capture and audit

Underneath, three commitments hold, reachable through *registro de la sesión*:

- **No interpretation is anonymous.** Every derived item records whether a
  researcher or the model produced it. Model-produced material carries the exact
  model id, endpoint and sampling settings that produced it.
- **Editing does not overwrite.** Changes append a revision recording the previous
  and new value.
- **Withdrawal is not deletion.** *Retirar* keeps the material, marks it withdrawn
  and stores the stated reason. *Eliminar* genuinely destroys the text and also
  redacts the quotations of it the session record itself had retained — and records
  that a redaction happened. The two are deliberately different operations.

*registro de la sesión* opens the append-only record, attributing every action to
`participante`, `investigador`, `modelo` or `sistema`, naming the model behind
each stage, and holding the JSON and Markdown exports. Both exports carry it.

The badge in the header says **LOCAL** and nothing else. Which model is running,
on which endpoint, under which settings, is one click away in the record: the
claim worth making in a room is that nothing leaves the machine, not a
quantisation suffix.

The manual annotation, derived-material and relation operations still exist in
the API, the data model and the exports; they are simply not surfaced in the
interface, because putting them on screen communicates bureaucracy rather than
accumulation.

### Example material

**Sesión de ejemplo** loads a single researcher-authored transcript that shows
capture and audit without a live model. It is written by the researcher, is not
participant testimony, and was never generated live. The interface labels it and
refuses new turns. Rebuild it with `python scripts/build_demo_session.py`.

`python scripts/build_demo_corpus.py` writes seven overlapping conversations into
`data/sessions/` so the field has something to accumulate. The transcripts are
authored; the **extractions are real**, produced by running the configured model
exactly as the application does, so model provenance in the graph is genuine
rather than fabricated. It therefore needs a configured model and takes a few
minutes. Re-running is safe and is the right thing to do after changing the
extraction policy: each conversation replaces its own previous build.

Appending `?session=<id>` or `?node=place:cerro` to the URL opens a specific
session or entity directly.

## Run locally

Python 3.11+ is recommended.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Configure an OpenAI-compatible Chat Completions endpoint:

```bash
export LLM_MODEL='YOUR_MODEL'
# optional; defaults to https://api.openai.com/v1/chat/completions
export LLM_API_URL='https://api.openai.com/v1/chat/completions'
# required by api.openai.com; optional for unauthenticated local servers
export LLM_API_KEY='YOUR_API_KEY'
```

`OPENAI_API_KEY` can be used instead of `LLM_API_KEY`.

For local evaluation, the prototype deliberately remains provider-neutral. Point
`LLM_API_URL` directly at any already-running OpenAI-compatible local server;
no Modelito dependency is required by this disposable code. Common examples are:

```bash
# Ollama OpenAI-compatible endpoint
export LLM_API_URL='http://127.0.0.1:11434/v1/chat/completions'
export LLM_MODEL='YOUR_OLLAMA_MODEL'
unset LLM_API_KEY OPENAI_API_KEY

# BaseRT commonly serves on 8080
# export LLM_API_URL='http://127.0.0.1:8080/v1/chat/completions'

# vllm-mlx and oMLX commonly serve on 8000
# export LLM_API_URL='http://127.0.0.1:8000/v1/chat/completions'
```

Modelito is useful alongside the prototype for local-runtime readiness and
workload benchmarking, while the prototype itself continues to exercise the
same OpenAI-compatible boundary that the eventual system may replace:

```bash
modelito-doctor --provider auto --model 'YOUR_MODEL'
modelito-benchmark-local --provider ollama --model 'YOUR_MODEL' --json
```

Use provider-specific model identifiers when comparing runtimes; an Ollama tag
should not be assumed to be identical to an MLX/Hugging Face model identifier.

### Target-machine evidence bundle

With the current `krahd/modelito` installed and one local server already
running, the complete non-participant evaluation can be recorded with one
command. For example:

```bash
python scripts/run_target_machine_evaluation.py \
  --provider ollama \
  --model 'YOUR_EXACT_MODEL_ID' \
  --chat-url 'http://127.0.0.1:11434/v1/chat/completions' \
  --repetitions 3
```

For BaseRT, vllm-mlx, oMLX, MLX-LM or another OpenAI-compatible endpoint, pass
the corresponding provider/model and, when necessary,
`--benchmark-base-url 'http://127.0.0.1:PORT/v1'`.

The command creates one ignored timestamped directory under
`evaluation/results/` containing:

- a manifest with machine/configuration metadata;
- raw responses to all ten researcher-authored scenarios;
- three generated multi-turn rhythm conversations;
- the independent Modelito conversational runtime benchmark.

It does **not** score conversational quality automatically. Manual review remains
separate and follows `docs/MANUAL-TESTS.md`. Full protocol and comparison rules
are in `evaluation/RUNBOOK.md`.

Start the web prototype:

```bash
bash start.sh
```

Or, with the environment already active:

```bash
uvicorn app:app --reload --port 8765
```

Open `http://127.0.0.1:8765`.

Without a configured model, the memory field, the chronology and session creation still run, but sending conversational turns and automatic extraction are disabled. This is deliberate: the prototype does not fake conversational quality with canned replies.

### VS Code

1. Copy `.env.example` to `.env` and fill in the endpoint and model you want to use. You can skip this step to explore the memory field without model-backed conversation.
2. Run **Tasks: Run Build Task** (`Cmd+Shift+B` on macOS) and choose **Prototype: Run**. The first run creates `.venv` and installs the dependencies.
3. Open `http://127.0.0.1:8765`.

The task reads `.env` automatically. Stop it with **Tasks: Terminate Task**. The additional **Prototype: Setup** and **Prototype: Test** tasks are available through **Tasks: Run Task**; setup prepares the environment and exits without keeping a server running.

## Constrained conversation controller

Participant utterances are treated as data, never application instructions.
Before interviewing, a router classifies memory/testimony, uncertainty,
correction, participant-control operations, and off-topic commands. Off-topic
commands receive a fixed application-owned redirect and never enter the
interviewing model. Model output is JSON-schema constrained to one conversational
move — `BACKCHANNEL`, `INVITE_CONTINUE`, `FOLLOW_UP`, `CLARIFY`, or
`ACKNOWLEDGE` — plus one complete utterance and an exact participant turn id.
The controller validates the move without rewriting its prose. Questions are
required only for follow-up and clarification; content-bearing moves must ground
in what the cited turn actually introduced, and recent assistant wording cannot
simply repeat. Control material remains in the immutable transcript with a
`non_testimony/control` label and is excluded from automatic extraction. Which
move produced a reply is recorded on the turn and shown in the session record,
not beside the conversation.

Set `LLM_ROUTER_MODEL` to a small local model; it also becomes the extraction
model unless `LLM_EXTRACTION_MODEL` overrides it. The 30B model is then used
only for substantive interview moves. Ollama calls use its native API so the
router/extractor context can be held to 4K and the interview context to 8K
(`LLM_*_CONTEXT_TOKENS`), allowing both models to remain resident with
`OLLAMA_KEEP_ALIVE=-1`. Startup warms them, and all calls reuse one HTTP client.
The interviewer receives the last 14 eligible turns plus exact older turns still
referenced by recent grounding, rather than an indefinitely growing transcript.

Two protections exist because of specific observed failures:

**Acknowledgement over hedged material.** An acknowledgement asserts without
asking, so it slips past every leading-question check. When the participant has
marked something as second-hand or uncertain, the guard requires the reply to
keep that distance, and no move may attribute knowledge, memory or certainty to
anyone the participant did not. This came from a live run in which the model
reported that a participant's mother "recordaba bien" what she had only been said
to talk about.

**Reported speech is not a control instruction.** Memories are full of other
people talking, and the control vocabulary is exactly the vocabulary of being
told to stop. "Y ahí él me dijo «basta, terminemos acá»" is testimony about a
moment; "me acuerdo que decía «borrá todo»" is not a deletion request. The
deterministic controller searches only the participant's own voice, with
quotation and reported clauses removed, and the router is told the same. Getting
this wrong would end a session in the middle of a memory about being told to stop
talking — or appear to accept a request to destroy the recording.

The researcher-authored cases remain in `evaluation/scenarios.json`, including one
in which the participant quotes somebody else telling them to stop and to destroy
something. A separate
multi-turn rhythm corpus in `evaluation/rhythm-scenarios.json` feeds every
generated assistant reply into the following turn so question frequency,
initiative, grounding and repetition can be reviewed as conversation rather than
as isolated outputs:

```bash
python scripts/run_rhythm_scenarios.py
```

## Optional local voice

The browser can run a continuous half-duplex local path through whisper.cpp and
Piper: listen, detect the end-of-turn silence, transcribe in Spanish, generate,
speak, then listen again **by itself**. *Hablar* starts the exchange and
*Terminar* ends it; nothing is pressed between turns. The microphone track is
disabled while the system is speaking, so there is no barge-in, while the stream
and analyser remain allocated for the next turn.

End of turn is 1.7 seconds of silence, not the ~1 second a command interface
would use. A memory conversation is full of hesitation, and a threshold tuned for
command-and-control speech cuts people off exactly where they are reaching for
something. This is demo turn detection, not archival VAD.

Run **Prototype: Voice Doctor** to see missing components. Installation, `.env`
configuration, provenance, and limits are in [`docs/VOICE.md`](docs/VOICE.md).

## Extraction does not compete with the conversation

Extraction runs behind the reply, which is an architectural separation. On a
single local server it also needs to be a computational one: an analysis call and
the next conversational call contend for the same weights, and it is the
participant who waits. Background extraction therefore also waits for the
conversational model to go quiet — no call in flight, and quiet for
`LLM_EXTRACTION_SETTLE` seconds, since somebody mid-thought speaks again within a
second or two. Queued extractions run one at a time, and an extraction already
in flight is cancelled and retried if a new conversational call arrives.

`LLM_EXTRACTION_MODEL` can select a different small model; otherwise extraction
reuses `LLM_ROUTER_MODEL` and leaves the conversational weights alone.
Interpretations are attributed to whichever model actually produced them, in
the record and in the exports.

The accumulated graph is cached by a field-specific version. The browser holds
one server-sent event stream and refreshes only when a recollection is stored or
an extraction changes the field; it no longer issues a timed polling burst after
every turn.

Nothing about this delays the field: the recollection is already visible while
extraction is still waiting.

## Tests

```bash
pytest -q
```

The deterministic tests cover transcript preservation, provenance, correction relations, editable derived material, exports, core interaction-policy invariants, local unauthenticated model configuration, and the target-machine evaluation tooling. CI runs the same suite on every push and pull request.

Naturalness cannot be established by unit tests. `docs/MANUAL-TESTS.md` contains researcher-authored Uruguayan-Spanish scenarios and a scoring rubric. Record actual model behaviour in `docs/TEST-REPORT.md` before claiming the interaction is validated.

## Data

Prototype sessions are written as local JSON under `data/sessions/` and ignored by git. Local evaluation evidence is written under `evaluation/results/` and ignored by git. Do not use real participant or sensitive testimony data in this disposable prototype without the appropriate research/governance route.

## Design boundary

The prototype deliberately does **not** solve authentication, final consent, production storage, security, archival schema, long-term stewardship, deployment, institutional governance, or final provider selection. Those decisions belong to the next phase, after interaction testing has produced evidence about what the system actually needs.
