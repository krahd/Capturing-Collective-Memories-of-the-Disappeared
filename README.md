# Capturing Collective Memories of the Disappeared

This repository is the dedicated implementation space for **Capturing Collective Memories of the Disappeared with Artificial Intelligence**, a research project on conversational systems for capturing dispersed, partial and situated memories connected to Uruguay's detained-disappeared.

It is distinct from `krahd/desaparecidos.uy`, the computational memorial artwork.

## Project objective

The central design problem is to capture collective memories of the disappeared. The conversational agent, provenance model, memory field, privacy architecture and other technical components exist in service of that objective.

The eventual system is intended to let people contribute memories, fragments, inherited accounts, uncertainty, corrections, relationships and associated media without requiring them to arrive with a polished testimony or to translate what they remember into archival/database categories first.

## Current phase

The code in this repository is intentionally a **disposable interaction prototype**. It exists to make interaction, representation and runtime failures concrete enough to test. It is not the architecture of the eventual research system and does not need to survive into it.

The current implementation goal is in [`GOAL.md`](GOAL.md); prototype rationale/non-goals are in [`PROTOTYPE.md`](PROTOTYPE.md); current state is in [`STATUS.md`](STATUS.md).

Long-lived production guidance is indexed in [`docs/README.md`](docs/README.md):

- [`docs/DESIGN-FOUNDATIONS.md`](docs/DESIGN-FOUNDATIONS.md) — project objective hierarchy, problem families and long-lived invariants;
- [`docs/COLLECTIVE-MEMORY-CAPTURE.md`](docs/COLLECTIVE-MEMORY-CAPTURE.md) — deferred collective significance and its consequences for live capture;
- [`docs/FUTURE-ARCHITECTURE.md`](docs/FUTURE-ARCHITECTURE.md) — mobile/full-duplex direction, capture/archive separation, privacy, consent, threat model and deployment questions;
- [`docs/EVALUATION-FRAMEWORK.md`](docs/EVALUATION-FRAMEWORK.md) — conversational, epistemic, accessibility, adversarial and representation evaluation.

The design docs link directly to the two research reviews maintained in `krahd/academic-writing`.

## What the prototype does

The interface has two explicit modes. **Contribuir** is the default participant view and shows no aggregate field. **Explorar el corpus** is a deliberately separate researcher view.

### Conversation

A participant-led text conversation, with optional fully local continuous half-duplex voice, driven by a policy for natural Uruguayan/Rioplatense Spanish, non-leading follow-up, digression, uncertainty, correction and refusal.

Participant turns are treated as data, not application instructions. A router separates testimony/uncertainty/correction from participant controls and off-topic commands. Explicit controls are handled by the application rather than delegated to the interviewer model.

The interviewer is restricted to five current move types:

- `BACKCHANNEL`
- `INVITE_CONTINUE`
- `FOLLOW_UP`
- `CLARIFY`
- `ACKNOWLEDGE`

Questions are not mandatory on every turn. The guard checks grounding, repeated wording and some forms of unsupported certainty without rewriting accepted model prose.

The current prototype does not yet implement a no-speech `WAIT/YIELD` move. Research/design work now identifies that as an important future experiment.

### Campo de memoria

The researcher mode is not an annotation workbench. A participant speaks in the separate capture mode and the field grows automatically.

A conventional knowledge graph might read `Person → Event → Place` and silently present derived structure as resolved historical fact. Here **recollections are first-class nodes**:

```text
Conversación 07
    ├── recuerdo r1 ── menciona ───────→ Julio
    │                └─ menciona lugar ─→ la facultad
    └── recuerdo r2 ── menciona fecha ──→ 1976
```

The field deliberately uses weak relations. Extraction establishes that a recollection mentioned something, not that an event occurred there, happened on that date, or that an extracted interpretation is true.

Uncertainty, hearsay and correction remain attached to the recollection that carries them. Contradictory datings can coexist.

#### Important prototype limitation

The current field shares extracted nodes across conversations by a conservatively normalised label. This makes possible convergence visible in a demo, but it is **not production identity resolution**.

Two people called `Julio` may be different people. `mi tío Aníbal` and `Aníbal` may refer to the same person, but the kinship relation also carries information that simple normalisation discards.

The production direction is mention-level evidence plus explicit, provisional coreference/identity hypotheses with provenance and revision history. See [`docs/COLLECTIVE-MEMORY-CAPTURE.md`](docs/COLLECTIVE-MEMORY-CAPTURE.md).

The `campo de memoria` is an apparatus for exposing relations among stored acts of recollection. It is not claimed to be collective memory itself.

### Staged growth

The field makes three stages visible:

1. the recollection appears as soon as the participant turn is stored;
2. provisional extraction arrives afterwards;
3. possible cross-conversation relations become visible if the prototype's extracted labels converge.

Preservation therefore does not depend on successful interpretation.

### Cronología

`Cronología` is the first built view produced from accumulated material. It keeps multiple dates rather than adjudicating them and always points back to source recollections.

Two-digit year conversion such as `el 76 → 1976` is a prototype heuristic. Production temporal interpretation must retain the exact phrase and treat normalised dates as provisional.

`Mapa`, `Búsqueda`, `Temas` and `Conexiones` remain deliberately unbuilt and are shown as such.

## Capture and audit

The raw participant transcript is not silently rewritten when derived material changes.

The stored model supports:

- exact turn preservation;
- original voice audio plus separate ASR-derived text;
- annotations and derived items with exact source-turn references;
- model/researcher origin and model configuration provenance;
- revision history rather than silent edit overwrite;
- withdrawal distinct from deletion;
- append-only event/audit record;
- JSON and Markdown export.

Manual annotation/derived/relation APIs remain available even though the participant-facing screen does not expose an annotation workflow.

## Performance architecture of the current prototype

The current local implementation avoids several unnecessary latency costs:

- routing, interviewing and extraction currently remain on the validated 30B model; an unsafe small router is not used for the meeting prototype;
- background extraction yields to live conversation and can be pre-empted;
- configured Ollama models are warmed/kept resident;
- interview context is bounded;
- HTTP connections are reused;
- aggregate memory-field/chronology views are cached;
- the browser receives field-change events rather than issuing a timed polling burst;
- resident `whisper-server` can keep ASR weights loaded across voice turns;
- the microphone stream/analyser remain allocated across continuous half-duplex turns.

Runtime details are documented in `.env.example`, `docs/VOICE.md` and the evaluation runbook.

## Current voice path

The disposable prototype supports a fully local continuous half-duplex loop:

```text
microphone → endpointing → ffmpeg → resident whisper.cpp
→ constrained interviewer → Piper → speakers → microphone again
```

The current end-of-turn heuristic defaults to **2.2 seconds** of detected silence and is configurable with `VOICE_END_OF_TURN_MS`. It is an experimental prototype parameter, not a claim about the correct duration of participant silence.

The microphone track is disabled while the system speaks, so the participant cannot barge in. That is a known prototype limitation.

The intended production system is **mobile-first, speech-first and full duplex**. Participant interruption should be easy; system interruption should be conservative. See [`docs/FUTURE-ARCHITECTURE.md`](docs/FUTURE-ARCHITECTURE.md).

Voice installation, configuration, source/transcript status and the empirical verification gate are in [`docs/VOICE.md`](docs/VOICE.md).

## Run locally

Python 3.11+ is recommended.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

Copy `.env.example` to `.env` and configure the model/runtime you want to test.

For a local Ollama deployment, the basic configuration is:

```bash
LLM_API_URL=http://127.0.0.1:11434/v1/chat/completions
LLM_MODEL=YOUR_OLLAMA_MODEL
LLM_ROUTER_MODEL=YOUR_SMALL_ROUTER_MODEL
OLLAMA_KEEP_ALIVE=-1
```

`LLM_EXTRACTION_MODEL` may override the extraction model. Without the override, a configured router model is also used for extraction.

Start the prototype:

```bash
bash start.sh
```

or, with the environment already active:

```bash
uvicorn app:app --reload --port 8765
```

Open `http://127.0.0.1:8765`.

Without a configured model, stored sessions, the memory field, chronology and session creation still work, but model-backed conversational turns and automatic extraction are disabled.

### VS Code

1. Copy `.env.example` to `.env` and configure the desired endpoint/models.
2. Run **Tasks: Run Build Task** (`Cmd+Shift+B` on macOS) and choose **Prototype: Run**.
3. Open `http://127.0.0.1:8765`.

Additional setup, test, voice installation and voice-doctor tasks are available under **Tasks: Run Task**.

## Demo and evaluation

- [`docs/DEMO.md`](docs/DEMO.md) — current prototype demonstration runbook;
- [`docs/MANUAL-TESTS.md`](docs/MANUAL-TESTS.md) — researcher-authored interaction tests;
- [`docs/TEST-REPORT.md`](docs/TEST-REPORT.md) — actual observed model evidence/failures;
- [`evaluation/RUNBOOK.md`](evaluation/RUNBOOK.md) — target-machine model/runtime comparison;
- [`docs/EVALUATION-FRAMEWORK.md`](docs/EVALUATION-FRAMEWORK.md) — long-term evidence hierarchy and evaluation dimensions.

Run deterministic tests with:

```bash
pytest -q
```

Naturalness, cultural validity, usability, safety and successful memory capture cannot be established by unit tests or LLM-as-judge scoring. They require the corresponding human and eventually participant evidence.

## Data

Ordinary prototype sessions are written to local JSON under `data/sessions/` and ignored by git. Meeting-demo sessions and audio are ephemeral, run-scoped and removed on explicit cleanup or application shutdown. The frozen synthetic seed corpus lives under `demo/corpus/`; local evaluation evidence is written under ignored `evaluation/results/`.

Do not use real participant or sensitive testimony data in this disposable prototype without the appropriate research, consent and governance route.

## Production boundary

The current prototype deliberately does not solve:

- final consent and participant review;
- privacy/differentiated access;
- relational privacy;
- production storage/security;
- corpus-integrity/adversarial threat model;
- mobile deployment;
- full-duplex production speech;
- offline/intermittent capture;
- production entity/coreference semantics;
- final archival stewardship;
- actual revocation propagation;
- institutional governance;
- final provider/runtime selection.

Do not infer production architecture from the fact that a shortcut exists in this code. Long-lived direction belongs to `docs/` and will be revised as empirical evidence accumulates.
