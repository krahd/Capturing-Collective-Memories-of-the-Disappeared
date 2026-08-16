# RTCA Experiment B2 TTFT replication

## Purpose

The frozen B2 run measured complete sequential model-request time but did not use streaming and therefore cannot yield time-to-first-token (TTFT) retrospectively. This replication keeps the B2 scenario/model/policy/repair design while enabling OpenAI-compatible streaming solely to measure model TTFT.

This is a **new replication**, not a rewrite of the frozen B2 evidence.

## Single entry point

```bash
python -m scripts.run_rtca_ttft_experiment
```

The runner uses the same five researcher-authored convergence scenarios, three-model matrix, five repetitions per model/scenario cell, deferred-significance policy, deterministic guard, and maximum of three candidate attempts per decision as B2. It writes a new timestamped result bundle under:

```text
evaluation/results/rtca-experiment-b2-ttft-<timestamp>/
```

It does not overwrite `rtca-experiment-b2-20260815T050113Z`.

## Runtime version

For the current target machine the user-supplied Ollama versions are:

- server: **0.32.5**;
- client: **0.32.9**.

The runner also captures the literal output of `ollama --version` in the result payload so the warning/version observation is preserved with the run.

## Measurement definitions

### Model TTFT

`ttft_ms` is measured from request dispatch to the first non-empty streamed `delta.content` chunk from the OpenAI-compatible chat endpoint. Empty/role-only chunks are ignored.

### Candidate completion

`completion_ms` is measured from request dispatch to completion of the streamed candidate.

### First token from decision start

For repaired candidates, `first_token_from_decision_start_ms` includes the complete elapsed time of all previous rejected attempts plus TTFT of the current attempt.

### Admission-ready time

The deterministic guard currently validates the completed JSON candidate. A streamed token therefore cannot safely be exposed to the participant as soon as it arrives: the architecture does not know whether the candidate will be admitted until generation is complete and the guard has run.

`admission_ready_ms` is therefore the sum of complete candidate-request times through the accepted attempt, or through all attempts before deterministic fallback.

This distinction is central to interpretation:

> **model TTFT is not equivalent to safe conversational response onset when admission control requires the completed candidate.**

A low TTFT can coexist with a much later admission-ready time.

## Warm-up

Each model receives one excluded streaming warm-up request before measured decisions. The TTFT run therefore characterises resident-model behaviour rather than first-load latency. The warm-up TTFT/completion is retained for provenance but excluded from experimental summaries.

## Outputs

The run stores:

- `experiment-b2-ttft.json`: complete matrix and attempt traces;
- `ttft-summary.json`;
- `ttft-summary.md`;
- `manifest.json`;
- per-model `models/<model-id>/experiment-b2-ttft.json` files.

For every attempt it retains:

- raw streamed model output after reassembly;
- parsed candidate;
- guard outcome;
- TTFT;
- completion time;
- first-token time from decision start;
- errors.

For every decision it retains:

- first-attempt TTFT;
- accepted-candidate TTFT;
- accepted-candidate first token from decision start;
- admission-ready time;
- delivery source and final intervention.

## Claim boundary

The run measures local language-model streaming and guard-mediated timing. It does not measure:

- microphone or VAD/endpointing latency;
- ASR;
- TTS;
- networked deployment latency;
- participant-perceived latency;
- barge-in or overlap;
- full-duplex conversational quality.

The wider **Capturing Collective Memories of the Disappeared with Artificial Intelligence** project is explicitly being developed toward a speech-first, full-duplex participant interface. The current disposable prototype remains half duplex. The production direction requires easy participant interruption, conservative system interruption, continuation across apparent turn boundaries, and immediate correction of an incorrect intervention. TTFT in this replication concerns one upstream component of that future full-duplex path.
