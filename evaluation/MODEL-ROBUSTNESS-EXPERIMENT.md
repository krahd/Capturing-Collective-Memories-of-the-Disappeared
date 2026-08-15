# RTCA model robustness experiment

## Purpose

The live-model evaluation treats the conversational model as an experimental factor rather than infrastructure. A policy that appears safe with one model may fail through question packing, over-specification, generic acknowledgement, epistemic hardening or excessive passivity with another. The objective is not to rank local models. It is to determine whether the interaction-policy findings survive changes in model scale and family, and where architectural guards are necessary because model behaviour is unstable.

## Frozen matrix

Canonical configuration: `evaluation/model-robustness-matrix.json`.

The matrix contains three Ollama-served instruction-tuned models:

1. **Primary:** `qwen3:30b-a3b-instruct-2507-q4_K_M` (`Qwen/Qwen3-30B-A3B-Instruct-2507`).
2. **Within-family scale control:** `qwen3:4b-instruct-2507-q4_K_M` (`Qwen/Qwen3-4B-Instruct-2507`).
3. **Cross-family control:** `mistral-small3.2:24b-instruct-2506-q4_K_M` (`mistralai/Mistral-Small-3.2-24B-Instruct-2506`).

All three use Ollama Q4_K_M representations and the same OpenAI-compatible serving endpoint. This keeps the model comparison separate from the runtime comparison. The Qwen 4B control tests scale inside one family. Mistral Small 3.2 tests whether results are peculiar to Qwen; its model card describes support for 24 languages and improvements in instruction following and repetition behaviour.

This matrix is a deliberate small panel. Adding many models would turn the experiment into an open-ended leaderboard and weaken the paper's systems question.

## Single entry point

From the implementation repository root:

```bash
python -m scripts.run_rtca_experiments
```

That command performs the complete pre-participant RTCA evidence run:

1. checks for `modelito-doctor` and `modelito-benchmark-local`;
2. if Modelito is absent, installs the sibling `../modelito` checkout when present, otherwise installs the pinned `krahd/modelito` commit recorded in `scripts/ensure_rtca_models.py`;
3. checks `ollama list` and runs `ollama pull` only for matrix models that are absent;
4. runs `modelito-doctor --provider ollama` for every frozen model;
5. reruns the Level-0 deferred-significance benchmark once as a mechanical sanity gate;
6. runs Experiment B for every model under all three frozen policy conditions;
7. uses five repetitions per scenario × policy × model by default, yielding **225 generated A-turn decisions** across the three-model matrix;
8. preserves every raw response, parse error, guard outcome and delivered intervention;
9. runs the conservative automatic evaluation separately for every model;
10. generates one manual-adjudication CSV per model;
11. runs an independent Modelito local-runtime benchmark for every model;
12. writes cross-model automatic summaries and a top-level manifest.

Use `--no-prepare` only when dependency/model preparation has deliberately been handled elsewhere. Use `--no-runtime-benchmark` only when runtime evidence is intentionally omitted. A custom one-model run is available through `--model`, but automatic pulling is restricted to the frozen matrix so an arbitrary user-supplied identifier is never downloaded silently.

## Experimental structure

The expanded design has three separable axes.

### Policy axis

For each model, compare:

- immediate-information;
- adaptive semi-structured;
- deferred-significance / low-injection.

This tests whether the proposed policy changes branch closure and contamination opportunities.

### Model axis

Compare the same frozen scenarios, policies and portable sampling fields across:

- Qwen3 30B-A3B primary;
- Qwen3 4B scale control;
- Mistral Small 3.2 24B cross-family control.

This tests policy robustness and policy × model interaction. A result that exists only for one model must be reported as model-specific.

### Runtime axis

Modelito timing evidence is recorded separately. Runtime measurements must not be combined into the interaction score. A faster model can still be conversationally unsafe; a slower model can be more restrained. The model experiment therefore uses one serving stack, while the earlier same-model runtime work remains the appropriate place for server/runtime comparisons.

## Sampling

The default portable generation fields remain:

- temperature: 0.7;
- top_p: 0.8;
- max_tokens: 256.

These are held constant across the model matrix for experimental comparability. This is not a claim that the same values are optimal for every model. Any later model-specific tuning must be a separate experiment because changing model and decoding together would confound the comparison.

## Outputs

A run creates `evaluation/results/rtca-model-matrix-<timestamp>/` with:

- `manifest.json`;
- `level0.json` and `level0.md`;
- `automatic-matrix-summary.json` and `.md`;
- `models/<model-id>/experiment-b.json`;
- `models/<model-id>/experiment-b-evaluation.json` and `.md`;
- `models/<model-id>/experiment-b-manual-review.csv`;
- `models/<model-id>/runtime-benchmark.json`.

The raw experiment files retain the model identifier and the frozen model specification. The manifest records preparation, failures, planned/completed counts and the exact paths needed for adjudication.

## Manual adjudication

Automatic screening is intentionally conservative and is not the final result. Complete every `human_*` field in each model's review CSV. Then run:

```bash
python -m scripts.run_rtca_experiments --summarise-matrix evaluation/results/rtca-model-matrix-<timestamp>
```

This produces `manual-matrix-summary.json`. Any incomplete row causes a non-zero completion status.

Manual interpretation should ask two distinct questions:

1. Did the intervention preserve the participant's possibility of continuing a later-significant branch?
2. Did it facilitate recollection without inserting historical propositions, specificity, certainty or presuppositions not supplied by the participant?

Do not reduce these to a single generic conversational-quality score.

## Interpretation

The most useful outcomes are not necessarily that the primary model wins. Four patterns are scientifically informative:

- **policy effect stable across models:** strongest evidence that the interaction design matters independently of one model;
- **policy × model interaction:** evidence that critical guarantees should be architectural rather than prompt-only;
- **small-model degradation:** evidence for a quality/latency trade-off in restraint, grounding or uncertainty preservation;
- **cross-family divergence:** evidence that claims must be bounded to tested model families and that model choice is itself part of the conditions of recollection.

The system should therefore not be framed as having discovered a uniquely appropriate model. The stronger design claim is that source preservation, provenance and critical guards do not rely on the model consistently embodying the project's epistemic commitments.

## Claim boundary

This experiment uses researcher-authored synthetic scenarios. It can support claims about tested model + policy configurations, branch-closing interventions, specified informational-contamination opportunities and interactional facilitation. It cannot establish human false-memory formation, participant trust, trauma-informed validity, historical truth or field effectiveness.

## Source records for the frozen controls

- Qwen3 model family and 2507 variants: `https://github.com/QwenLM/Qwen3` and the corresponding Hugging Face model cards.
- Mistral Small 3.2 source model: `https://huggingface.co/mistralai/Mistral-Small-3.2-24B-Instruct-2506`.
- Ollama tags: `https://ollama.com/library/qwen3/tags` and `https://ollama.com/library/mistral-small3.2/tags`.
