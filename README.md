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
