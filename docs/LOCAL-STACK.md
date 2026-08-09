# Local conversational stack

**Status:** disposable prototype configuration, reviewed against upstream runtime/model documentation on 8 August 2026.

The first tests should run entirely on the local machine. This is useful both for privacy during development and because conversational latency can be measured without network variance. None of the choices below are commitments for the production architecture.

## Runtime policy

The prototype uses Modelito for text-model selection and MLX-Audio as a separate local speech service.

Modelito exposes two paths:

- `portable`: Ollama only. This is the common macOS/Linux/Windows route.
- `mac-performance`: BaseRT, then oMLX, then Ollama on Apple Silicon.

The order is a current default, not a universal speed ranking. Override it with `MODELITO_LOCAL_PREFER` after measuring the target Mac and workload.

Current evidence:

- BaseRT is a native-Metal Apple-Silicon runtime with an OpenAI-compatible server. Its July 2026 paper reports higher decode throughput than MLX and llama.cpp on the tested M3/M4 systems, and larger prefill gains in some workloads: <https://arxiv.org/abs/2607.00501>.
- BaseRT server/API documentation: <https://docs.basecompute.co/quickstart> and <https://docs.basecompute.co/server-api>.
- Ollama's 2026 Apple-Silicon engine now uses MLX, has prefix/snapshot caching, lower memory use and faster TTFT/generation, so it should not be treated as merely a slow fallback: <https://ollama.com/blog/mlx-performance>.
- Ollama's current Gemma 4 MLX model is available as `gemma4:12b-mlx`: <https://ollama.com/library/gemma4:12b-mlx>.
- oMLX remains useful for MLX-native serving, continuous batching and persistent paged/prefix KV caching. Modelito already has an oMLX provider.

### Why BaseRT is first but not mandatory

BaseRT's published benchmarks are not measurements of this M1 Max, and raw tokens/second do not determine conversational performance. Long-prefix prefill, time to first token, cache reuse, memory shared with speech models and thermal behaviour can change the ranking. If oMLX or Ollama is better on the actual prototype workload, change the preference rather than preserving the default.

## Text model baseline

The initial quality baseline is **Gemma 4 12B**, rather than a tiny model chosen only for speed. The target machine has enough unified memory to test a 12B quantised model together with the small speech models, but this still needs measurement.

Provider-specific identifiers are configured separately:

```bash
export LOCAL_MODEL_BASERT='gemma-4-12B'
export LOCAL_MODEL_OMLX='mlx-community/gemma-4-12B-4bit'
export LOCAL_MODEL_OLLAMA='gemma4:12b-mlx'
```

The oMLX conversion is approximately 11 GB and the Ollama MLX package approximately 7.7 GB according to their current model pages. These are storage/model-package figures, not promises about resident memory.

### Portable Ollama path

Install current Ollama and obtain the model:

```bash
ollama run gemma4:12b-mlx
```

Then:

```bash
export MODELITO_LOCAL_PROFILE='portable'
```

### BaseRT path

Install BaseRT following its official instructions. BaseRT can pull Hugging Face repositories and convert them locally. For Gemma, access may require the normal Hugging Face/Gemma credentials and licence acceptance.

A representative setup is:

```bash
basert pull google/gemma-4-12B
basert serve --model google/gemma-4-12B --port 8080
```

Inspect `GET /v1/models` after starting the server and set `LOCAL_MODEL_BASERT` to the model ID that the server exposes to OpenAI-compatible requests. If the server is protected with `--api-key`, also set:

```bash
export BASERT_API_KEY='...'
```

The prototype defaults to BaseRT at `http://127.0.0.1:8080/v1`. Override with `BASERT_BASE_URL`.

### oMLX path

Run an oMLX OpenAI-compatible server and load the desired MLX model. The prototype expects it at `http://localhost:8000/v1` unless `OMLX_BASE_URL` is set.

For a machine-specific ordering, for example:

```bash
export MODELITO_LOCAL_PROFILE='mac-performance'
export MODELITO_LOCAL_PREFER='omlx,basert,ollama'
```

## Speech

Do not implement ASR/TTS inference in this prototype. **MLX-Audio already provides an OpenAI-compatible local speech server on Apple Silicon**, including `/v1/audio/transcriptions` and `/v1/audio/speech`, plus current support for Qwen3-ASR, Qwen3-TTS, Whisper, Parakeet and other architectures: <https://github.com/Blaizzy/mlx-audio>.

Run the MLX-Audio server on a different port from oMLX. The prototype defaults to:

```bash
export AUDIO_BASE_URL='http://127.0.0.1:8001/v1'
```

The first low-latency baseline is:

```bash
export STT_MODEL='mlx-community/Qwen3-ASR-0.6B-8bit'
export TTS_MODEL='mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit'
```

The current MLX model pages report approximately 1.01 GB for the Qwen3-ASR 0.6B 8-bit package and 1.99 GB for the Qwen3-TTS 0.6B Base 8-bit package:

- <https://huggingface.co/mlx-community/Qwen3-ASR-0.6B-8bit>
- <https://huggingface.co/mlx-community/Qwen3-TTS-12Hz-0.6B-Base-8bit>

The 0.6B TTS model is a latency-oriented starting point, not a quality conclusion. Compare it with the 1.7B Qwen3-TTS model before deciding.

### ASR alternatives to compare

At minimum compare the baseline against:

1. `mlx-community/parakeet-tdt-0.6b-v3`, which supports 25 European languages including Spanish;
2. a current Whisper large-v3-turbo MLX build as a robustness baseline;
3. Qwen3-ASR 1.7B if the 0.6B model makes material recognition errors;
4. Voxtral Realtime only if streaming latency justifies its larger footprint.

Recognition quality must be tested on **Uruguayan speech**, especially names, places, dates, voseo, hesitation, corrections and discourse particles. Generic Spanish benchmark results are insufficient for this project.

### TTS evaluation

A voice being labelled Spanish or multilingual does not establish that it sounds appropriate to a Uruguayan listener. Test rhythm, pronunciation, register, foreign accent, excessive expressiveness and the pronunciation of Uruguayan names/places.

The text of the assistant reply remains canonical. Synthesised speech is an interface rendering of that reply, not a separate memory record.

## Interaction decision: transcription is editable before sending

The browser records a short microphone turn and sends it to the local ASR endpoint. The resulting text is placed in the normal message box and **is not submitted automatically**. The participant/tester can correct names or recognition errors first.

This is deliberate. In this project, a mistaken proper name, date or hedge can materially alter the record. Low-friction conversation does not justify silently accepting ASR output as participant speech.

A future full-duplex experiment can use upstream VAD/realtime facilities once the basic interaction is good enough. Do not build a custom VAD/barge-in stack before testing the facilities already supplied by MLX-Audio and the chosen runtime.

## M1 Max 64 GB test protocol

Run the same scenarios for each candidate configuration. Record the runtime/model versions and whether each turn was cold or warm.

Measure:

- end of participant speech to provisional transcript;
- ASR corrections required, with special attention to names, hedges and dates;
- message submission to first model token if the runtime exposes it;
- message submission to complete assistant text;
- complete assistant text to first audible speech;
- end of participant speech to first audible assistant response;
- response length and whether excessive verbosity itself creates latency;
- latency at turns 1, 5, 10, 20 and 40 as the conversational prefix grows;
- memory pressure with LLM, ASR and TTS resident together;
- behaviour after at least 20 minutes of interaction;
- naturalness scores from `docs/MANUAL-TESTS.md`;
- recognition and synthesis failures, not only averages.

For this application **turn latency and interaction quality matter more than maximum decode tokens/second**.

## First comparison matrix

| Layer | Low-latency baseline | Alternatives worth testing |
| --- | --- | --- |
| LLM runtime, portable | Ollama MLX | — |
| LLM runtime, Mac | BaseRT | oMLX; Ollama MLX |
| LLM | Gemma 4 12B | smaller Gemma 4 E4B for latency; larger/other multilingual models only if needed |
| STT | Qwen3-ASR 0.6B 8-bit | Parakeet v3; Whisper large-v3-turbo; Qwen3-ASR 1.7B; Voxtral Realtime |
| TTS | Qwen3-TTS 0.6B Base 8-bit | Qwen3-TTS 1.7B; other MLX-Audio multilingual models if voice quality is inadequate |

The matrix is intentionally small. The purpose is to learn what the interaction needs, not to conduct a general local-AI benchmark.
