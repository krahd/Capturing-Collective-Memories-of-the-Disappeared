# Capturing Collective Memories of the Disappeared

This repository is the dedicated implementation space for **Capturing Collective Memories of the Disappeared with Artificial Intelligence**, a research project on conversational interfaces for eliciting and preserving dispersed, partial and situated memories connected to Uruguay's detained-disappeared.

It is a different project from `desaparecidos.uy`, the computational memorial artwork.

## Current phase

The current code is intentionally a **disposable interaction prototype**. Its purpose is to make the conversational interaction and the apparatus for working on a conversation concrete enough to test. The prototype is not the architecture of the eventual research system and does not need to survive into it.

The current goal is defined in `GOAL.md`; interaction rationale and non-goals are in `PROTOTYPE.md`.

## What the prototype does

It has two coordinated views:

- **Conversation**: participant-led text conversation, driven by a compact policy for natural Uruguayan Spanish, non-leading follow-up, digression, uncertainty, correction and refusal.
- **Mesa de trabajo**: select transcript turns, annotate them, create or model-extract provisional entities/events/themes, edit derived material, connect corrections/qualifications, and export the whole session.

The raw transcript is never silently rewritten when derived material changes.

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
export LLM_API_KEY='YOUR_API_KEY'
# optional; defaults to https://api.openai.com/v1/chat/completions
export LLM_API_URL='https://api.openai.com/v1/chat/completions'
```

`OPENAI_API_KEY` can be used instead of `LLM_API_KEY`.

Start:

```bash
bash start.sh
```

Or, with the environment already active:

```bash
uvicorn app:app --reload --port 8765
```

Open `http://127.0.0.1:8765`.

Without a configured model, the workbench and session creation still run, but sending conversational turns and automatic extraction are disabled. This is deliberate: the prototype does not fake conversational quality with canned replies.

## Tests

```bash
pytest -q
```

The deterministic tests cover transcript preservation, provenance, correction relations, editable derived material, exports, and core interaction-policy invariants. CI runs the same suite on every push and pull request.

Naturalness cannot be established by unit tests. `docs/MANUAL-TESTS.md` contains researcher-authored Uruguayan-Spanish scenarios and a scoring rubric. Record actual model behaviour in `docs/TEST-REPORT.md` before claiming the interaction is validated.

## Data

Prototype sessions are written as local JSON under `data/sessions/` and ignored by git. Do not use real participant or sensitive testimony data in this disposable prototype without the appropriate research/governance route.

## Design boundary

The prototype deliberately does **not** solve authentication, final consent, production storage, security, archival schema, long-term stewardship, deployment, institutional governance, or final provider selection. Those decisions belong to the next phase, after interaction testing has produced evidence about what the system actually needs.
