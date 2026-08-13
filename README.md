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
    ├── recuerdo r1 ── menciona ──→ Julio
    │                └─ ocurre en ─→ la facultad
    └── recuerdo r2 ── fecha ─────→ 1976
```

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

Below the graph, **Extraído** counts what exists and **Puede producir** names
what the material could support — timeline, map, search, themes, connections.
Those are deliberately not built yet; they are there to show the archive is
computationally productive.

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
`participante`, `investigador`, `modelo` or `sistema`. Both exports carry it.

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
minutes.

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

Without a configured model, the workbench and session creation still run, but sending conversational turns and automatic extraction are disabled. This is deliberate: the prototype does not fake conversational quality with canned replies.

### VS Code

1. Copy `.env.example` to `.env` and fill in the endpoint and model you want to use. You can skip this step to run the workbench without model-backed conversation.
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
`non_testimony/control` label and is excluded from automatic extraction.

The original ten cases remain in `evaluation/scenarios.json`. A separate
multi-turn rhythm corpus in `evaluation/rhythm-scenarios.json` feeds every
generated assistant reply into the following turn so question frequency,
initiative, grounding and repetition can be reviewed as conversation rather than
as isolated outputs:

```bash
python scripts/run_rhythm_scenarios.py
```

## Optional local voice

The browser can run a half-duplex local path through whisper.cpp and Piper:
listen, detect the end-of-turn silence, transcribe in Spanish, generate, speak,
then listen again. Run **Prototype: Voice Doctor** to see missing components.
Installation, `.env` configuration, provenance, and limits are in
[`docs/VOICE.md`](docs/VOICE.md).

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
