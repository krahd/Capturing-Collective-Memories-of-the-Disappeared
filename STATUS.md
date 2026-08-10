# Status

**Date:** 9 August 2026  
**Phase:** disposable interaction prototype  
**Implementation:** complete for the current interaction-discovery goal  
**Mechanical verification:** passing  
**Live-model Uruguayan-Spanish evaluation:** pending on target machine

## Implemented

- two coordinated views: Conversation and Mesa de trabajo;
- provider-neutral OpenAI-compatible conversational model integration;
- authenticated hosted endpoints and unauthenticated local OpenAI-compatible endpoints;
- interaction policy targeting natural adult Uruguayan/Rioplatense Spanish without caricature or questionnaire behaviour;
- exact turn-by-turn transcript preservation;
- annotations and uncertainty/hearsay/correction/withdrawal/significance labels;
- provisional manual and model-derived entities/events/places/times/themes with exact source-turn provenance;
- editable and deletable derived material without transcript mutation;
- correction/qualification/contradiction/reference relations;
- JSON and Markdown export;
- local JSON session persistence ignored by git;
- automated CI verification;
- ten executable researcher-authored Uruguayan-Spanish evaluation scenarios;
- live-model scenario recorder retaining exact context and raw output;
- one-command target-machine evidence bundler combining conversational outputs, machine/configuration metadata and the independent Modelito benchmark;
- explicit portable sampling controls for comparable conversational runs (`temperature`, `top_p`, `max_tokens`);
- target-machine runbook and primary local-model selection record.

## Local-model evaluation path

The earlier credential blocker has been removed. `LLM_API_KEY` is still required for the default `api.openai.com` endpoint, but it is optional for local OpenAI-compatible servers. The disposable prototype therefore remains independent of any specific inference runtime.

Modelito is used alongside, not inside, this prototype. Its local-runtime layer can discover/benchmark Ollama, BaseRT, vllm-mlx and oMLX, while this repository tests the same OpenAI-compatible conversational boundary against whichever runtime/model is selected. This keeps runtime engineering separate from interaction claims.

The primary local model selected for the first controlled RTCA evaluation is **Qwen3-30B-A3B-Instruct-2507**. The exact deployment forms and comparability caveats are recorded in `evaluation/MODEL-SELECTION.md`. The selection is an experimental starting point, not a claim that this is the final or best model for Uruguayan Spanish.

The principal target-machine entry point is:

```bash
python scripts/run_target_machine_evaluation.py \
  --provider PROVIDER \
  --model 'EXACT_MODEL_ID' \
  --chat-url 'http://127.0.0.1:PORT/v1/chat/completions' \
  --repetitions 3
```

It creates one ignored timestamped evidence directory under `evaluation/results/` with:

- `manifest.json`: machine/configuration metadata, exact model/runtime identity and fixed conversational sampling fields;
- `conversation-scenarios.json`: exact researcher-authored scenario contexts and raw model responses;
- `runtime-benchmark.json`: independent Modelito first-request/warm-prefix/context/cancellation measurements.

The conversational runs default to `temperature=0.7`, `top_p=0.8`, `max_tokens=256`; the Modelito timing benchmark independently uses deterministic sampling for timing comparability. These outputs must not be merged into one score.

Complete HTTP round-trip latency from the prototype is not TTFT and does not establish interruption or server-side cancellation behaviour. Those runtime properties belong to the separate Modelito conversational benchmark.

## Verification

GitHub Actions is green on the current main branch. The suite verifies Python/browser syntax and deterministic tests covering transcript preservation, source traceability, derived editing/deletion, correction relations, export, policy invariants, local model configuration, explicit generation settings, scenario-corpus integrity, both evaluation runners and the end-to-end API flow.

## Remaining goal gate

The remaining evidence gate is physical and empirical rather than architectural: execute the primary Qwen3-30B-A3B-Instruct-2507 comparison on the target Apple-Silicon machine and review the actual model responses using `docs/MANUAL-TESTS.md`.

The cleanest runtime comparison is MLX-LM / oMLX / vllm-mlx using the same MLX model files. BaseRT and Ollama can use the same upstream Qwen weights in their current 4-bit deployment forms, but those results are a realistic runtime-plus-representation comparison rather than a pure runtime benchmark.

The conversational review must remain human/researcher-authored. The dimensions are conversational following, Uruguayan naturalness, non-leading behaviour, preservation of uncertainty, participant agency and economy. No claim of naturalness, usability, cultural validity, safety or successful memory capture should be made before the corresponding evidence exists.

For RTCA, runtime measurements remain separate: first-request TTFT, warm-prefix TTFT, context-growth behaviour, first useful streamed phrase, decode rate and cancellation/stream-close behaviour. These are design inputs, not substitutes for conversational evaluation.

Issue #1 remains open until the local runs are actually executed and reviewed.

## After the prototype test round

Do not incrementally harden this code into the production system by default. Use observed interaction failures and successful operations to design the actual architecture from first principles, including consent, governance, ownership, access, security, voice/duplex interaction and archival stewardship.
