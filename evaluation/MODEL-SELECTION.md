# Local model selection for the RTCA evaluation

**Decision updated:** 14 August 2026

## Experimental principle

The conversational model is an experimental factor, not neutral infrastructure. A policy that appears to preserve uncertainty, avoid suggestion and leave conversational space with one model may fail with another. Model scale, instruction tuning, multilingual competence and learned helpfulness priors can all affect question density, epistemic hardening, inference and passivity.

The evaluation therefore separates three questions:

1. **policy:** does the interaction policy reduce branch closure and informational injection under a fixed model?
2. **model robustness:** does that result survive changes in model scale and family under one serving stack?
3. **runtime:** how do serving/runtime choices affect latency for the same model/weights where practical?

Do not collapse these into one leaderboard.

## Frozen model-robustness panel

Canonical machine-readable configuration: `evaluation/model-robustness-matrix.json`.

### Primary model

**Qwen3-30B-A3B-Instruct-2507**

Ollama tag:

`qwen3:30b-a3b-instruct-2507-q4_K_M`

Source weights:

`Qwen/Qwen3-30B-A3B-Instruct-2507`

This remains the primary model because it is an instruction-tuned, non-thinking conversational model in a useful quality/latency regime for the target Apple-Silicon machine, with broad multilingual support and established local-runtime paths. It is not presumed to be the best Spanish-language model or the final production model.

### Within-family scale control

**Qwen3-4B-Instruct-2507**

Ollama tag:

`qwen3:4b-instruct-2507-q4_K_M`

Source weights:

`Qwen/Qwen3-4B-Instruct-2507`

This is no longer optional. It is the planned scale control. It tests whether a much smaller model changes restraint, grounding, uncertainty preservation and policy compliance while providing a substantially different latency regime.

### Cross-family control

**Mistral-Small-3.2-24B-Instruct-2506**

Ollama tag:

`mistral-small3.2:24b-instruct-2506-q4_K_M`

Source weights:

`mistralai/Mistral-Small-3.2-24B-Instruct-2506`

This is the cross-family control. Its source model supports 24 languages and the 3.2 update specifically targets instruction following and repetition behaviour. It is included to test whether the policy results are peculiar to Qwen, not because the experiment is intended to establish a general model ranking.

## Why three models, not many

The minimum informative panel needs:

- one primary model;
- one same-family scale control;
- one different-family instruction-tuned multilingual control.

A larger panel would add cost and multiple-comparison surface while pulling the paper towards model benchmarking. Additional models should only be added if one of these three cannot execute reliably or if the first results expose a specific hypothesis that requires another control.

## Serving-stack discipline

For the **model-robustness experiment**, all three frozen models use Ollama and Q4_K_M representations where available. This deliberately keeps the serving stack constant while model family/scale changes.

For the **runtime experiment**, the primary Qwen3-30B-A3B model can still be compared across MLX-LM, oMLX, vllm-mlx, BaseRT and Ollama. The MLX-LM/vllm-mlx/oMLX subset can use identical MLX files; BaseRT/MLX/Ollama comparisons remain runtime + representation comparisons unless quantisation equivalence is demonstrated.

Do not interpret model-robustness differences as runtime differences, and do not interpret runtime comparisons as model-quality comparisons.

## Automatic preparation

The canonical single entry point is:

```bash
python -m scripts.run_rtca_experiments
```

Before generation it:

- checks for Modelito;
- installs the sibling `../modelito` checkout if available, otherwise the pinned `krahd/modelito` commit declared in `scripts/ensure_rtca_models.py`;
- checks `ollama list`;
- runs `ollama pull` only for frozen matrix models that are absent;
- runs `modelito-doctor --provider ollama --model ...` for each model.

Custom arbitrary model identifiers are never automatically downloaded. A custom run requires `--model ... --no-prepare`.

## Conversation sampling

For the researcher-authored model comparison, portable generation settings are fixed across all models:

- `temperature = 0.7`;
- `top_p = 0.8`;
- `max_tokens = 256`.

Holding these constant is an experimental-control decision, not a claim that they are individually optimal for every model. Model-specific decoding optimisation would confound model identity with sampling and must be treated as a separate experiment.

Qwen's additional recommendations such as `top_k` are not consistently exposed through the common OpenAI-compatible interface and therefore are not silently treated as fixed.

Modelito's independent runtime benchmark uses its own timing-oriented deterministic settings. Runtime evidence remains separate from conversational evaluation.

## Planned decision count

Each frozen model runs:

5 scenario families × 3 policies × 5 repetitions = **75 decisions**.

The complete model matrix therefore produces **225 generated A-turn decisions**, all retained.

This allows examination of:

- policy effects within each model;
- scale effects within Qwen;
- cross-family robustness;
- policy × model interactions;
- whether lower contamination/closure is achieved through useful facilitation rather than generic silence.

## Interpretation

A model-sensitive result does not invalidate the architecture. It strengthens the case for moving critical guarantees out of prompt-level behaviour where possible. Source preservation, provenance, one-question constraints and deterministic contamination guards should remain defensible even when model behaviour changes.

The desired conclusion is therefore not “model X is the correct interviewer”. The stronger question is which conversational properties remain stable across models and which require architectural enforcement.

## Current sources

- Qwen3 official repository: https://github.com/QwenLM/Qwen3
- Qwen3 source model cards: https://huggingface.co/Qwen
- Mistral Small 3.2 model card: https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506
- Ollama Qwen3 tags: https://ollama.com/library/qwen3/tags
- Ollama Mistral Small 3.2 tags: https://ollama.com/library/mistral-small3.2/tags
- Modelito: https://github.com/krahd/modelito
