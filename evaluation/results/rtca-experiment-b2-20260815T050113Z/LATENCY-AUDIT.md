# RTCA Experiment B2 latency audit

**Date:** 15 August 2026  
**Run:** `rtca-experiment-b2-20260815T050113Z`  
**Scope:** descriptive timing of the already-frozen B2 run; no models were rerun.

## What is measured

The B2 runner records `round_trip_ms` for each HTTP model request and `total_round_trip_ms` as the sum of sequential requests made before an intervention is delivered. A rejected proposal can therefore spend conversational time even though the participant never hears it.

These values are **not** streaming time-to-first-token, speech endpointing time, TTS time, or participant-perceived reply latency. They are accumulated local model-request times for this run and machine. They should not be interpreted as a general model benchmark.

## Descriptive results

| Model | n | Median total decision | p90 total decision | First-attempt acceptance | Repair acceptance | Final fallback |
|---|---:|---:|---:|---:|---:|---:|
| Qwen3-30B-A3B | 25 | 2.51 s | 2.99 s | 0/25 | 24/25 | 1/25 |
| Qwen3-4B | 25 | 1.93 s | 2.56 s | 6/25 | 14/25 | 5/25 |
| Mistral Small 3.2 | 25 | 7.09 s | 10.80 s | 6/25 | 17/25 | 2/25 |

The first recorded decision for each model was unusually slow: 27.50 s for Qwen3-30B, 11.77 s for Qwen3-4B, and 13.85 s for Mistral. Removing only that first recorded decision changes the median/p90 to 2.50/2.85 s, 1.89/2.43 s, and 6.98/10.67 s respectively. The central result therefore does not depend on those first-decision outliers.

Where the same model produced both first-attempt and repaired acceptances, repair had a visible temporal cost:

| Model | First-attempt accepted median | Repaired accepted median |
|---|---:|---:|
| Qwen3-4B | 0.80 s | 1.99 s |
| Mistral Small 3.2 | 3.20 s | 7.31 s |

Qwen3-30B produced no first-attempt acceptance in B2. Its 24 repaired acceptances had a median accumulated request time of 2.50 s.

## Interpretation

B2 was introduced to prevent a rejected intervention from collapsing immediately to deterministic fallback. Mechanically, it succeeds: fallback drops sharply. But repair is itself an interactional action because it consumes time before anything can be delivered. The system can therefore trade one form of restraint failure for another: an intervention that is more admissible may arrive late enough to alter turn-taking, invite overlap, or make a minimal backchannel disproportionately expensive.

This sharpens the RTCA problem. Epistemic restraint, conversational initiative, and response time cannot be treated as independent objectives. The present run is too narrow to establish an optimal trade-off, and it does not measure perceived latency, but it is sufficient to show that sequential guard-aware regeneration is not a cost-free safety layer.

## Calculation notes

Statistics were calculated over the 25 retained `total_round_trip_ms` values for each frozen model. `p90` uses the standard linear percentile over those observations. Conditional medians use the recorded `accepted_attempt`: attempt 1 for first-pass acceptance and attempts 2–3 for repaired acceptance. No inferential statistics are reported because the five scenario families with stochastic repetitions are not treated as 75 independent real-world conversations.

## Claim boundary

This audit supports only a descriptive systems claim about the frozen local run. It does not establish participant tolerance for delay, conversational naturalness, speech timing quality, model-family speed in general, or any human-memory outcome.
