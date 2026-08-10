# Local model selection for the RTCA evaluation

**Decision date:** 9 August 2026

## Primary comparison model

Use **Qwen3-30B-A3B-Instruct-2507** as the primary local conversational model for the first target-machine evaluation.

This choice is deliberately narrower than selecting a permanent production model. It provides a strong common target for the current interaction/runtime experiment because:

- it is an instruction-tuned, non-thinking conversational model rather than a chain-of-thought-oriented reasoning variant;
- the source model has 30.5B total parameters with approximately 3.3B activated per token, giving a useful quality/latency regime for an M1 Max with 64 GB unified memory;
- Qwen3 was trained for broad multilingual use and the 2507 Instruct update explicitly improves multilingual knowledge and open-ended preference alignment;
- current Q4/4-bit builds derived from the same source weights are available for BaseRT, MLX and Ollama;
- vllm-mlx, oMLX and raw MLX-LM can therefore be compared using the same MLX model files, making that subset of the runtime comparison especially clean.

The project is **not** claiming that this is the best Spanish-language model or the final production model. The ten Uruguayan-Spanish scenarios exist precisely to test whether its interaction is acceptable for this research use.

## Exact model identifiers

### Source weights

`Qwen/Qwen3-30B-A3B-Instruct-2507`

### BaseRT

`basecompute/Qwen3-30B-A3B-Instruct-2507`

The current BaseRT build is Q4 and approximately 17 GB.

### MLX-LM / vllm-mlx / oMLX

`mlx-community/Qwen3-30B-A3B-Instruct-2507-4bit`

Use the same downloaded MLX files for all three runtimes whenever their server configuration permits it.

### Ollama

Prefer the explicit current tag rather than an ambiguous moving alias:

`qwen3:30b-a3b-instruct-2507-q4_K_M`

The Ollama build is Q4_K_M and approximately 19 GB.

## What is and is not comparable

The **MLX-LM / vllm-mlx / oMLX** comparison can use the exact same MLX weights. Differences are therefore primarily serving/runtime differences, subject to server configuration and cache state.

The **BaseRT / MLX / Ollama** comparison uses the same upstream model weights but different 4-bit conversion/quantisation formats. This is a realistic deployment comparison, not a mathematically pure runtime benchmark. Report it as **runtime + representation** unless the conversion formats can be made demonstrably equivalent.

Do not silently substitute a different model when a runtime cannot load the selected build. Record incompatibility as a result and, if necessary, run a second explicitly labelled comparison family.

## Conversation sampling

For the researcher-authored scenario evaluation, the target-machine wrapper now fixes the portable OpenAI-compatible fields to:

- `temperature = 0.7`;
- `top_p = 0.8`;
- `max_tokens = 256`.

The first two match the source model's recommended generation settings. The response cap is intentionally much smaller than the model's general-purpose recommendation because the prototype's interaction policy asks for brief conversational turns.

Qwen also recommends `top_k = 20` and `min_p = 0`. These are not standard OpenAI Chat Completions fields across all local servers. If a runtime exposes them, standardise them where possible and record the exact server configuration. Do not pretend that they were fixed when a server does not expose them through the common API.

Modelito's independent runtime benchmark uses `temperature = 0` for timing comparability. Its timing results must therefore remain separate from the sampled conversational outputs.

## Primary run order

Run the same primary model in this order only for operational convenience; this is not a ranking:

1. MLX-LM reference;
2. oMLX;
3. vllm-mlx;
4. BaseRT;
5. Ollama.

The first three should use the exact same MLX model directory/files. Stop each server before starting the next unless there is a specific reason to test simultaneous residency.

For every run, use `scripts/run_target_machine_evaluation.py` so the scenario outputs, machine/configuration metadata and Modelito benchmark remain in the same evidence bundle.

## Optional scale control

If time permits, repeat the protocol with **Qwen3-4B-Instruct-2507** as a small-model control. BaseRT has a Q4 build and corresponding MLX/Ollama forms are available. The purpose is not to replace the 30B-A3B model by default, but to expose whether the conversational requirements fail at a much smaller model scale even when latency improves substantially.

Do not add a larger panel of models before the primary Qwen3-30B-A3B-Instruct-2507 run has been reviewed. The current research question is interaction architecture and real-time mediation, not an open-ended local-model leaderboard.

## Current sources

- Qwen3 official repository and Qwen3-2507 documentation: https://github.com/QwenLM/Qwen3
- Qwen3-30B-A3B-Instruct-2507 model card: https://huggingface.co/Qwen/Qwen3-30B-A3B-Instruct-2507
- BaseRT Q4 build: https://huggingface.co/basecompute/Qwen3-30B-A3B-Instruct-2507
- MLX 4-bit build: https://huggingface.co/mlx-community/Qwen3-30B-A3B-Instruct-2507-4bit
- Ollama Qwen3 tags: https://ollama.com/library/qwen3/tags
- vllm-mlx: https://github.com/waybarrios/vllm-mlx
- oMLX: https://github.com/jundot/omlx
