# Capturing Collective Memories of the Disappeared

This repository is the dedicated implementation space for **Capturing Collective Memories of the Disappeared with Artificial Intelligence**, a research project on conversational interfaces for eliciting and preserving dispersed, partial and situated memories connected to Uruguay's detained-disappeared.

It is a different project from `desaparecidos.uy`, the computational memorial artwork.

## Current phase

The current code is intentionally a **disposable interaction prototype**. Its purpose is to make the conversational interaction and the apparatus for working on a conversation concrete enough to test. The prototype is not the architecture of the eventual research system and does not need to survive into it.

The current goal is defined in `GOAL.md`; interaction rationale and non-goals are in `PROTOTYPE.md`. The local-model/speech configuration and current runtime research are in `docs/LOCAL-STACK.md`.

## What the prototype does

It has two coordinated views:

- **Conversation**: participant-led conversation driven by a compact policy for natural Uruguayan Spanish, non-leading follow-up, digression, uncertainty, correction and refusal. Input can be typed or locally transcribed from the microphone; ASR text remains editable before it is sent.
- **Mesa de trabajo**: select transcript turns, annotate them, create or model-extract provisional entities/events/themes, edit derived material, connect corrections/qualifications, and export the whole session.

The raw transcript is never silently rewritten when derived material changes.

## Local-first model stack

The prototype no longer requires a hosted LLM API. Text generation is selected through the development branch of `modelito`:

- `portable`: Ollama;
- `mac-performance`: BaseRT → oMLX → Ollama on Apple Silicon;
- selection order can be overridden after machine-specific benchmarking.

Speech uses a separate local **MLX-Audio** OpenAI-compatible service. The initial low-latency defaults are Qwen3-ASR 0.6B 8-bit and Qwen3-TTS 0.6B Base 8-bit. These are testing baselines, not final model choices.

See `docs/LOCAL-STACK.md` before installing models. It records the upstream evidence, alternatives and M1 Max evaluation protocol.

## Install the prototype

Python 3.11+ is recommended.

```bash
python3 -m venv .venv
. .venv/bin/activate
pip install -r requirements.txt
```

The requirements currently install Modelito directly from its `feature/local-runtime-profiles` branch so the prototype can exercise the new local-only selection API before that work is merged/released.

### Portable text path

With current Ollama installed:

```bash
ollama run gemma4:12b-mlx
export MODELITO_LOCAL_PROFILE='portable'
```

### Mac-performance path

Run one or more supported local servers, then use:

```bash
export MODELITO_LOCAL_PROFILE='mac-performance'
# optional benchmark-derived override:
# export MODELITO_LOCAL_PREFER='omlx,basert,ollama'
```

Provider-specific model/environment variables are documented in `docs/LOCAL-STACK.md`.

### Speech

Run MLX-Audio separately, by default on port 8001, and configure if needed:

```bash
export AUDIO_BASE_URL='http://127.0.0.1:8001/v1'
export STT_MODEL='mlx-community/Qwen3-ASR-0.6B-8bit'
export TTS_MODEL='mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit'
```

The app checks the local services at runtime. It does not download models automatically.

## Start

```bash
bash start.sh
```

Or, with the environment already active:

```bash
uvicorn app:app --reload --port 8765
```

Open `http://127.0.0.1:8765`.

If no local LLM is ready, the workbench and session creation still run but conversational sending and automatic extraction are disabled. If MLX-Audio is not ready, text conversation still works but microphone/TTS controls are disabled. The prototype does not fake model readiness with canned replies.

## Tests

```bash
pytest -q
```

CI also compiles the Python modules and syntax-checks the browser JavaScript. Deterministic tests cover transcript preservation, provenance, correction relations, editable/deletable derived material, exports, interaction-policy invariants, local-runtime configuration, speech request shapes and end-to-end API operations without downloading models.

Naturalness cannot be established by unit tests. `docs/MANUAL-TESTS.md` contains researcher-authored Uruguayan-Spanish scenarios and a scoring rubric. Record actual model behaviour in `docs/TEST-REPORT.md` before claiming the interaction is validated.

## Data

Prototype sessions are written as local JSON under `data/sessions/` and ignored by git. Do not use real participant or sensitive testimony data in this disposable prototype without the appropriate research/governance route.

## Design boundary

The prototype deliberately does **not** solve authentication, final consent, production storage, security, archival schema, long-term stewardship, deployment, institutional governance or final provider selection. Those decisions belong to the next phase, after interaction testing has produced evidence about what the system actually needs.
