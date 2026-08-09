# Status

**Date:** 9 August 2026  
**Phase:** disposable interaction prototype  
**Implementation:** complete for the current interaction-discovery goal  
**Mechanical verification:** passing  
**Live-model Uruguayan-Spanish evaluation:** pending on target model/runtime

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
- reproducible live-model evaluation harness using the ten researcher-authored scenarios.

## Local-model evaluation path

The earlier credential blocker has been removed. `LLM_API_KEY` is still required for the default `api.openai.com` endpoint, but it is optional for local OpenAI-compatible servers. The disposable prototype therefore remains independent of any specific inference runtime.

Modelito is used alongside, not inside, this prototype. Its local-runtime layer can discover/benchmark Ollama, BaseRT, vllm-mlx and oMLX, while this repository tests the same OpenAI-compatible conversational boundary against whichever runtime/model is selected. This keeps runtime engineering separate from interaction claims.

The live scenario runner is:

```bash
python scripts/run_live_scenarios.py
```

It writes ignored local JSON under `evaluation/results/`, recording the exact synthetic/researcher-authored context, the model response, model/endpoint identity and complete HTTP round-trip latency. It does not automatically score conversational quality.

Round-trip latency from this prototype is not TTFT and does not establish interruption or server-side cancellation behaviour. Those runtime properties belong to the separate Modelito conversational benchmark.

## Verification

GitHub Actions passed after enabling local unauthenticated model configuration on 9 August 2026. The suite verifies Python/browser syntax and deterministic tests covering transcript preservation, source traceability, derived editing/deletion, correction relations, export, policy invariants, local model configuration and the end-to-end API flow.

The evaluation harness also has deterministic tests confirming that all ten scenarios are machine-readable and that the runner can start independently of model credentials.

## Remaining goal gate

The remaining evidence gate is empirical rather than architectural: run the ten scenarios against the intended local model(s) on the target machine and review the actual responses using `docs/MANUAL-TESTS.md`.

This review must remain human/researcher-authored. The dimensions are conversational following, Uruguayan naturalness, non-leading behaviour, preservation of uncertainty, participant agency and economy. No claim of naturalness, usability, cultural validity, safety or successful memory capture should be made before the corresponding evidence exists.

For RTCA, runtime measurements should be recorded separately with Modelito: first-request TTFT, warm-prefix TTFT, context-growth behaviour, first useful streamed phrase, decode rate and cancellation/stream-close behaviour. These are design inputs, not substitutes for conversational evaluation.

Issue #1 remains open until the live conversations are actually run and reviewed.

## After the prototype test round

Do not incrementally harden this code into the production system by default. Use observed interaction failures and successful operations to design the actual architecture from first principles, including consent, governance, ownership, access, security, voice/duplex interaction and archival stewardship.
