# RTCA B2 streaming TTFT replication — audit

**Run:** `rtca-experiment-b2-ttft-20260816T025921Z`  
**Committed:** `df6e2a00e7cc1af8756c7e3c01f65ecfa3a71bb2`  
**Code under test:** `bfe4c8cdbc5529e1dfc972ceddeecac9724567e8`  
**Ollama observation:** server 0.32.5; client 0.32.9 (version-mismatch warning retained in the manifest)  
**Evidence:** researcher-authored synthetic streaming replication; no human subjects or participant testimony.

## Verdict

The replication strengthens the RTCA timing argument, but not because TTFT is large. The opposite is more interesting: **models often begin streaming quickly, while the current admission architecture cannot safely expose that stream until substantially later**.

The guard validates a completed JSON intervention. Consequently, first-token latency and safe response onset are different quantities. Repair compounds the difference because rejected candidates consume generation time before a replacement begins.

This produces a concrete systems result:

> **Fast model TTFT does not imply fast admissible conversational response when safety/epistemic restraint is enforced after complete generation.**

That distinction is directly relevant to the project's planned full-duplex voice path: streaming generation can begin inside a plausible turn-taking window while guard-mediated admission can remain too late to exploit it.

## Primary results

| Model | n | TTFT median / p90 | Accepted token from decision start median / p90 | Admission-ready median / p90 | Fallback |
|---|---:|---:|---:|---:|---:|
| Qwen3-30B-A3B | 25 | 164 / 347 ms | 1,549 / 1,734 ms | 1,755 / 1,938 ms | 1/25 |
| Qwen3-4B | 25 | 205 / 476 ms | 884 / 1,033 ms | 1,365 / 2,447 ms | 6/25 |
| Mistral Small 3.2 | 25 | 252 / 613 ms | 2,555 / 4,157 ms | 4,084 / 6,008 ms | 4/25 |

The first column is first-attempt model TTFT. `Accepted token from decision start` includes prior rejected attempts when the accepted intervention is a repair. `Admission-ready` is the earliest point at which the current completed-candidate guard could permit delivery.

## Magnitude of the admission gap

Using medians, admission-ready time is approximately:

- **10.7× first-attempt TTFT** for Qwen3-30B-A3B;
- **6.6×** for Qwen3-4B;
- **16.2×** for Mistral Small 3.2.

These ratios are descriptive of this local run and architecture, not universal model characteristics. They are nevertheless useful because they expose where latency is introduced: not only in model token onset, but in complete-candidate generation, rejection and repair.

For the primary model, the contrast is especially clean:

- first-attempt TTFT median: **164 ms**;
- accepted-candidate TTFT median: **358 ms**;
- accepted candidate's first token from the start of the whole decision: **1.549 s**;
- admission-ready median: **1.755 s**.

The model can start speaking quickly in computational terms, yet the present architecture cannot know that the utterance is admissible until roughly an order of magnitude later.

## Relation to the frozen B2 run

This is a stochastic replication, not a timing retrofit of the original B2 decisions. Its behavioural outcomes therefore need not reproduce the exact earlier counts.

Original B2 fallback:

- Qwen3-30B-A3B: 1/25;
- Qwen3-4B: 5/25;
- Mistral Small 3.2: 2/25.

Streaming replication fallback:

- Qwen3-30B-A3B: 1/25;
- Qwen3-4B: 6/25;
- Mistral Small 3.2: 4/25.

Do not silently combine these runs as if they were the same 75 decisions. The replication supports the timing mechanism; the original frozen B2 remains the canonical behavioural result used for its qualitative audit.

## What this changes in the paper

The strongest timing claim is no longer merely that sequential repair adds request latency. It is:

1. model TTFT can be sub-second and, for the primary model, around 164 ms median;
2. the current guard cannot admit partial output because it requires the completed JSON candidate;
3. rejected candidates can consume a substantial part of the turn-taking window before repair starts;
4. therefore a production full-duplex system cannot obtain both early speech onset and current fail-closed admission simply by turning on streaming;
5. admission itself must become compatible with streaming, or the interaction policy must explicitly decide when silence/yield is preferable to waiting for a repaired utterance.

This is a systems-design implication, not evidence that any particular latency is acceptable to participants.

## Full-duplex project context

This experiment is one component of **Capturing Collective Memories of the Disappeared with Artificial Intelligence**. The project is being developed towards a **voice-based, full-duplex participant interface** in which participant interruption is easy, system interruption is conservative, and correction can occur before an erroneous intervention finishes.

The present text-generation experiments deliberately isolate the language-policy/admission layer upstream of ASR and TTS. Their relevance to full duplex lies in the timing budget they consume before speech can safely begin, not in a claim that they already evaluate full-duplex interaction.

## Claim boundary

Supported:

- TTFT, accepted-token-from-decision-start and admission-ready descriptive statistics for this local streaming replication;
- the architectural distinction between first generated token and first currently admissible response;
- the observation that complete-candidate admission and repair can dominate TTFT;
- the need to account for admission latency in a future full-duplex pipeline.

Not supported:

- participant-perceived latency;
- acceptable human turn-taking thresholds;
- full-duplex naturalness or overlap quality;
- ASR/VAD/TTS latency;
- a universal model-speed ranking;
- superiority of one model or policy;
- participant benefit or memory outcomes.
