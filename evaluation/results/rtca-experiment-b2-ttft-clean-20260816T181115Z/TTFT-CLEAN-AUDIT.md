# RTCA B2 clean streaming timing replication — audit

**Run:** `rtca-experiment-b2-ttft-clean-20260816T181115Z`  
**Raw result commit:** `1ec5442779ef842d23c01029d0427acd9c8b1303`  
**Code under test:** `c86cb169fb82cb8644c01c93c400f8c0220b47c5`  
**Evidence:** researcher-authored synthetic streaming replication; no human subjects or participant testimony.

## Reproducibility state

This run removes the avoidable runtime ambiguities in the earlier exploratory streaming replication:

- Ollama client: **0.32.9**;
- Ollama server: **0.32.9**;
- dedicated local `ollama serve` process;
- explicit context length: **8192** via `OLLAMA_CONTEXT_LENGTH`;
- fixed candidate-request seed schedule beginning at **42**;
- one excluded warm-up request per model;
- 75/75 planned decisions completed.

The fixed seed schedule is recorded in the result manifest as `seed_base + zero-based request index` in deterministic sequential request order; warm-up requests do not consume indices. The original B1/B2 behavioural run remains unchanged and retains its earlier reproducibility limitations. This clean run is the canonical timing replication for the RTCA paper.

## Primary results

| Model | n | Fallback | First-attempt candidate-stream onset median / p90 | Accepted-candidate stream onset from decision start median / p90 | Admission-ready median / p90 |
|---|---:|---:|---:|---:|---:|
| Qwen3-30B-A3B | 25 | **0/25** | **166 / 352 ms** | **1,559 / 1,781 ms** | **1.771 / 1.988 s** |
| Qwen3-4B | 25 | **4/25** | **162 / 244 ms** | **801 / 937 ms** | **1.219 / 1.948 s** |
| Mistral Small 3.2 | 25 | **2/25** | **253 / 617 ms** | **2,565 / 4,845 ms** | **4.067 / 6.486 s** |

`First-attempt candidate-stream onset` is request dispatch to the first non-empty streamed `delta.content` chunk. `Accepted-candidate stream onset from decision start` includes complete time spent on rejected attempts before the first streamed chunk of the candidate that ultimately survives admission. `Admission-ready` is the earliest point at which the present completed-candidate guard can permit delivery.

The model returns a structured JSON candidate of the form `{"move": ..., "utterance": ...}`. The first non-empty content chunk can therefore precede the participant-facing `utterance` field. Both stream-onset measures are **lower bounds on participant-facing utterance onset**, not measurements of speech onset.

## Comparison with the earlier exploratory streaming run

Earlier exploratory run: `rtca-experiment-b2-ttft-20260816T025921Z`.

The principal timing pattern reproduces closely for the primary Qwen3-30B and Mistral models:

- Qwen3-30B first-attempt candidate-stream onset: **164.1 → 166.3 ms** (+1.3%); accepted-candidate stream onset: **1549.0 → 1559.5 ms** (+0.7%); admission-ready: **1755.1 → 1771.4 ms** (+0.9%).
- Mistral first-attempt candidate-stream onset: **251.9 → 252.8 ms** (+0.4%); accepted-candidate stream onset: **2554.6 → 2565.0 ms** (+0.4%); admission-ready: **4084.4 → 4066.6 ms** (-0.4%).
- Qwen3-4B is faster in the clean run: first-attempt candidate-stream onset **205.4 → 162.2 ms** (-21.0%); accepted-candidate stream onset **883.7 → 800.5 ms** (-9.4%); admission-ready **1365.2 → 1219.2 ms** (-10.7%).

The earlier client/server mismatch therefore does not explain the paper's primary timing result. The clean run should nevertheless replace the exploratory run in submission-facing numbers because its runtime provenance is stronger.

## Relation to original frozen B2

Original B2 fallback:

- Qwen3-30B-A3B: **1/25**;
- Qwen3-4B: **5/25**;
- Mistral Small 3.2: **2/25**.

Clean streaming fallback:

- Qwen3-30B-A3B: **0/25**;
- Qwen3-4B: **4/25**;
- Mistral Small 3.2: **2/25**.

The runs are not pooled. Original B2 remains the canonical behavioural/qualitative run because it supplies the audited minimal-backchannel and Rioplatense stress-case evidence. The clean run supplies canonical streaming timing evidence.

## Paper-facing interpretation

For Qwen3-30B, the first candidate stream begins after **166 ms** median, but the candidate that ultimately survives admission does not begin streaming until **1.56 s** from decision start and cannot be delivered under completed-candidate admission until **1.77 s** median. Across all three models, most of the median admission interval elapses before the accepted candidate stream begins.

Supported claim:

> Fast candidate-stream onset does not imply fast admissible speech under an architecture that serially generates, rejects, repairs and then validates complete candidates.

This is an architectural timing result. The stream-onset numbers are not speech-onset measurements and do not establish a human latency threshold or full-duplex conversational performance.

## Claim boundary

Not supported by this run:

- participant-facing utterance onset as a directly measured timestamp;
- participant-perceived latency;
- acceptable turn-taking thresholds;
- ASR/VAD/TTS latency;
- full-duplex naturalness, overlap or barge-in quality;
- interviewing quality or participant benefit;
- memory outcomes or false-memory prevention;
- model superiority.
