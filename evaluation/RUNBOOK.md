# Target-machine evaluation runbook

**Purpose:** produce reproducible evidence for the current disposable interaction prototype and the NeurIPS 2026 RTCA short paper without conflating conversational quality with inference performance.

**Target machine:** Tomas Laurenzo's Apple-Silicon development machine. The runtime comparison is only authoritative for the actual machine and configurations measured.

## Evidence boundary

This protocol uses only the ten researcher-authored cases in
`evaluation/scenarios.json` and the three researcher-authored multi-turn scripts
in `evaluation/rhythm-scenarios.json`. It is not a participant study and must
not be described as one.

Two independent evidence layers are produced:

1. **Conversation evidence:** exact model responses to the ten cases plus three
   generated multi-turn exchanges, manually reviewed with the existing rubric
   and rhythm criteria.
2. **Runtime evidence:** latency, context-growth, decoding and cancellation measurements from Modelito.

Do not collapse them into a single score. A fast model/runtime may be conversationally unsuitable; an appropriate conversational model may be too slow for sustained interaction.

## 1. Freeze the environment

Record before each comparison:

```bash
sw_vers
uname -m
sysctl -n machdep.cpu.brand_string 2>/dev/null || true
python3 --version
```

Also record manually:

- Mac model and unified-memory capacity;
- macOS version;
- Modelito commit/version;
- inference runtime name and version;
- exact model identifier;
- model parameter family/size where known;
- quantisation/precision where known;
- server launch command and non-default flags;
- endpoint;
- whether the model was already loaded/warm;
- whether other large local models/processes were resident.

Provider identifiers are not interchangeable. An Ollama tag and an MLX/Hugging Face model identifier must not be treated as the same model merely because their display names resemble each other.

## 2. Prefer comparable model families

For runtime comparison, use the same underlying model family, parameter count and as-close-as-practical quantisation/precision across runtimes. If exact equivalence is unavailable, record the difference and do not interpret the result as a pure runtime benchmark.

For conversational comparison, it is legitimate to compare different local models. Label that experiment **model + runtime evaluation**, not runtime evaluation.

Do not select a model because it is convenient to install if its Uruguayan/Rioplatense Spanish is clearly inadequate for the research question.

## 3. Start one local server at a time

The current Modelito candidate set is:

- BaseRT;
- vllm-mlx;
- oMLX;
- Ollama;
- raw MLX-LM as a reference path where appropriate.

Typical endpoints in the current Modelito documentation are:

- BaseRT: `http://127.0.0.1:8080/v1`;
- vllm-mlx: `http://127.0.0.1:8000/v1`;
- oMLX: `http://127.0.0.1:8000/v1`;
- Ollama OpenAI-compatible API: `http://127.0.0.1:11434/v1`.

vllm-mlx and oMLX commonly default to the same port. Use distinct ports only if they must remain resident simultaneously; otherwise prefer one server at a time so memory pressure and cache state are easier to interpret.

Do not run a hosted API during the local-runtime comparison.

## 4. Confirm readiness without mutation

From an environment with the current Modelito installed:

```bash
modelito-doctor --provider auto --model 'EXACT_MODEL_ID'
```

For a specific runtime, use its provider name where supported:

```bash
modelito-doctor --provider basert --model 'EXACT_MODEL_ID'
modelito-doctor --provider vllm-mlx --model 'EXACT_MODEL_ID'
modelito-doctor --provider omlx --model 'EXACT_MODEL_ID'
modelito-doctor --provider ollama --model 'EXACT_MODEL_ID'
```

The doctor is a read-only readiness probe. A successful readiness result establishes availability, not performance or conversational adequacy.

## 5. Run the ten conversational scenarios

Configure the disposable prototype directly against the already-running OpenAI-compatible server:

```bash
export LLM_API_URL='http://127.0.0.1:PORT/v1/chat/completions'
export LLM_MODEL='EXACT_MODEL_ID'
unset LLM_API_KEY OPENAI_API_KEY
```

Then run:

```bash
python scripts/run_live_scenarios.py
```

The runner writes an ignored JSON file under `evaluation/results/` containing:

- exact scenario context;
- raw response;
- model identifier;
- endpoint;
- complete non-streaming HTTP round-trip time;
- errors.

The recorded round-trip time is **not TTFT** and must not be used as a substitute for the Modelito benchmark.

Repeat the scenario run if needed to detect obvious stochastic instability, but preserve each run separately. Do not select only the best-looking outputs.

## 6. Manual conversational review

Before scoring, also run the multi-turn rhythm corpus:

```bash
python scripts/run_rhythm_scenarios.py
```

Unlike the isolated cases, each generated assistant response becomes context for
the next participant turn. Review the full exchange for question frequency,
move variation, concrete grounding, proportional initiative, and repetition.

Review every raw output against `docs/MANUAL-TESTS.md` using the six 0–2 dimensions:

- seguimiento;
- naturalidad;
- no conducción;
- incertidumbre;
- agencia;
- economía.

Treat a zero in **no conducción**, **incertidumbre**, or **agencia** as a critical failure irrespective of aggregate score.

For each runtime/model combination, retain at least:

- per-scenario scores;
- total/mean only as secondary summaries;
- every critical failure;
- representative strong responses;
- terse qualitative notes explaining why a response passed or failed;
- exact raw response linked to the score.

The most paper-useful evidence is likely to be a small number of representative interaction failures and repairs, not a single aggregate number.

## 7. Run the Modelito conversational benchmark separately

Examples:

```bash
modelito-benchmark-local \
  --provider basert \
  --model 'EXACT_MODEL_ID' \
  --repetitions 3 \
  --json \
  --output 'evaluation/results/basert-benchmark.json'
```

```bash
modelito-benchmark-local \
  --provider vllm-mlx \
  --model 'EXACT_MODEL_ID' \
  --repetitions 3 \
  --json \
  --output 'evaluation/results/vllm-mlx-benchmark.json'
```

```bash
modelito-benchmark-local \
  --provider omlx \
  --model 'EXACT_MODEL_ID' \
  --repetitions 3 \
  --json \
  --output 'evaluation/results/omlx-benchmark.json'
```

```bash
modelito-benchmark-local \
  --provider ollama \
  --model 'EXACT_MODEL_ID' \
  --repetitions 3 \
  --json \
  --output 'evaluation/results/ollama-benchmark.json'
```

Raw MLX-LM may be used as a reference label:

```bash
modelito-benchmark-local \
  --provider mlx-lm \
  --model 'EXACT_MODEL_ID' \
  --repetitions 3 \
  --json \
  --output 'evaluation/results/mlx-lm-benchmark.json'
```

If a server PID is known, `--pid SERVER_PID` adds approximate process-RSS sampling. On macOS this can under-report total Metal/unified-memory pressure, so record it as an approximation only.

## 8. Cold/warm discipline

For each runtime/model pair, decide in advance whether a run is intended to measure:

- a genuinely cold model start;
- first request to an already-loaded server;
- warm repeated conversational context.

Modelito's `first_request` is only a cold-model metric when the model was genuinely cold before the benchmark. Record cache/server state explicitly.

Warm-prefix TTFT is especially relevant here because the interaction repeatedly resends or reuses an expanding conversation history. Do not rank runtimes from decode tokens/s alone.

## 9. Cancellation caveat

Modelito records client stream-close latency and performs a post-cancellation probe. This does **not** prove that a server acknowledged and completed cancellation internally. If a runtime exposes native cancellation diagnostics, retain those separately.

For the future voice prototype, cancellation after participant barge-in should become a first-class experiment because a model that continues speaking after the narrator resumes can create epistemic interference even when average TTFT is excellent.

## 10. Comparison table

Populate one row per exact model/runtime/configuration.

| Runtime | Exact model | Precision / quantisation | First TTFT | Warm-prefix TTFT | Context-growth behaviour | First useful phrase | Decode t/s | Cancellation observation | Approx. memory | Conversation score | Critical failures |
|---|---|---|---:|---:|---|---:|---:|---|---:|---:|---|
| | | | | | | | | | | | |

Do not merge rows representing materially different model weights/quantisations into a single runtime average.

## 11. Paper inclusion rule

Only include empirical numbers in the RTCA manuscript when all of the following are true:

- the exact runtime/model/configuration is recorded;
- the measurement is reproducible from retained output;
- compared conditions are sufficiently similar for the claim being made;
- the metric means what the prose says it means;
- conversational scores remain clearly separate from runtime metrics;
- no participant-validation claim is inferred from researcher-authored scenarios.

If these conditions are not met by submission time, retain the manuscript as a short/position paper and describe the protocol rather than publishing weak numbers.

## 12. Stop condition for this prototype phase

The disposable prototype phase is sufficiently informative to move to architectural design when:

1. at least one local model/runtime can complete all ten cases and the three
   multi-turn rhythm conversations without systematic critical failures;
2. the remaining failures are characterised rather than hidden by prompt iteration;
3. latency/context-growth behaviour is known well enough to determine whether text streaming is viable;
4. observed conversational requirements are written independently of this prototype's code;
5. the next architecture can specify where consent, governance, voice turn-taking, raw media, derived interpretations and model mediation live.

This stop condition does not require real testimony collection. Real participant work belongs to the separately governed research phase.
