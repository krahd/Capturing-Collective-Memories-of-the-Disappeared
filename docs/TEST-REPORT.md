# Prototype test report

**Updated:** 15 August 2026  
**Participant evidence:** none. All current RTCA experiments use researcher-authored synthetic material.  
**Purpose:** record observed behaviour and failures without promoting mechanical checks into claims about people.

Design requirements derived from this evidence live in [`DESIGN-FOUNDATIONS.md`](DESIGN-FOUNDATIONS.md), [`COLLECTIVE-MEMORY-CAPTURE.md`](COLLECTIVE-MEMORY-CAPTURE.md), [`FUTURE-ARCHITECTURE.md`](FUTURE-ARCHITECTURE.md), and [`EVALUATION-FRAMEWORK.md`](EVALUATION-FRAMEWORK.md).

## RTCA experiment sequence — 14–15 August 2026

### Level 0 invariant suite

The frozen deferred-significance suite passed **16/16** checks:

- 5 delayed cross-session convergence checks;
- 3 non-collapse checks preserving contradiction, unlocated time and uncertainty;
- 8 deterministic controller/guard probes.

This establishes implementation behaviour only: preservation before interpretation, later relation emergence without source rewriting and nominated guard invariants. It does not show that a model interviews well or that a participant remembers better.

### B1: intervention-system comparison

B1 ran five researcher-authored scenario families, five stochastic repetitions, three intervention systems and three local Q4_K_M models, for **225/225 completed decisions** with no model-request failures.

The automatic delivered-surface screen marked possibility preservation in:

- immediate-information: **29/75 (38.7%)**;
- adaptive semi-structured: **37/75 (49.3%)**;
- deferred-significance: **71/75 (94.7%)**.

That result is deliberately not treated as a policy leaderboard. The immediate and adaptive comparators are prompt-only, while deferred significance additionally uses the production intervention-admission guard. The automatic screen also penalises several structures the guard is designed to reject. The 94.7% therefore demonstrates enforcement of nominated surface constraints within a different intervention system, not independent superiority of the prompt policy.

The guard-path audit is more informative. Deferred-condition deterministic fallback occurred in:

- Qwen3-30B-A3B: **25/25**;
- Qwen3-4B: **20/25**;
- Mistral Small 3.2: **18/25**.

The primary model could appear perfectly restrained because every candidate was replaced by `Contame.`. This exposed a failure in the safeguard itself: a system can reduce contamination opportunities by becoming interactionally inert.

### B2: guard-aware repair

B2 asks whether rejection can trigger another model attempt rather than immediate fallback. It retained the same five scenario families and three-model panel, with up to two repair attempts after the first candidate. **75/75 decisions completed.**

Final deterministic fallback fell from B1 to B2:

| Model | B1 | B2 |
|---|---:|---:|
| Qwen3-30B-A3B | 100% | **4%** |
| Qwen3-4B | 80% | **20%** |
| Mistral Small 3.2 | 72% | **8%** |

This is a mechanical success, but not yet successful interviewing. Qwen3-30B produced 22/25 minimal backchannels, two short acknowledgements and one fallback; no substantive grounded question survived. Mistral also remained dominated by minimal backchannels/acknowledgements. The 4B model produced more active questions but repeatedly exposed a different failure.

### Lexical admission is not semantic fidelity

For the source phrase:

> `A veces caía por el bar de la esquina, creo.`

B1 included the explicit physical-fall interpretation `¿qué tipo de caída ocurrió?`. In B2, all five corresponding Qwen3-4B trials admitted variants of `¿Podrías decirme más sobre cómo caía por el bar de la esquina?` through the deterministic structural/lexical admission checks.

In Rioplatense usage, `caer por` here means roughly to drop by. The failure is deliberately narrow: one expression, one scenario family, one model. It nevertheless shows why the mechanism should not be described as semantic grounding merely because it verifies source overlap and structural constraints.

### B2 latency

Repair is also a real-time operation. The runner records each local HTTP request and sums sequential attempts into `total_round_trip_ms`.

| Model | Median total decision | p90 |
|---|---:|---:|
| Qwen3-30B-A3B | **2.51 s** | 2.99 s |
| Qwen3-4B | **1.93 s** | 2.56 s |
| Mistral Small 3.2 | **7.09 s** | 10.80 s |

For models that produced both first-pass and repaired acceptances, median accumulated request time moved from **0.80 to 1.99 s** for Qwen3-4B and from **3.20 to 7.31 s** for Mistral. Qwen3-30B had no first-pass acceptance.

These values are not streaming TTFT, speech endpointing, TTS or participant-perceived response latency. They are descriptive request timings from the frozen local run. Full calculation and outlier sensitivity are in [`../evaluation/results/rtca-experiment-b2-20260815T050113Z/LATENCY-AUDIT.md`](../evaluation/results/rtca-experiment-b2-20260815T050113Z/LATENCY-AUDIT.md).

### Current empirical conclusion

The experiments do not show a monotonically safer interviewer. They show a changing failure surface. Tightening epistemic restraint can move a system among:

- informational injection;
- deterministic fallback;
- interactional minimalism;
- semantically distorted but structurally admissible probing;
- delay.

That is the current result. The `human_*` coding fields remain empty, so no quantitative rates are reported for facilitation, semantic distortion, inserted noise, naturalness, cultural adequacy or participant benefit.

## Earlier prototype evidence — 12–13 August 2026

The following observations predate B1/B2 but remain useful as implementation history.

### Conversation/controller

The earliest constrained controller over-specified surface form: every allowed action effectively became acknowledgement plus question, often repeating `Te sigo`. Revisions separated five moves (`BACKCHANNEL`, `INVITE_CONTINUE`, `FOLLOW_UP`, `CLARIFY`, `ACKNOWLEDGE`) and permitted zero-question replies.

Single- and multi-turn researcher-authored checks exposed:

- presupposition after hearsay;
- stilted acknowledgement such as `Acepto.`;
- repeated `¿Y cómo era...?` frames;
- packed questions despite an explicit one-question instruction;
- reformulation that could harden uncertain memory;
- ambiguous pronoun clarification;
- certainty-hardening such as describing a reported memory as remembered `bien`.

Those failures motivated deterministic admission checks. B1/B2 then demonstrated that increasingly restrictive admission can itself collapse interaction or admit lexically grounded semantic errors.

### Routing

A 49-case adversarial routing run produced no retained critical failure after deterministic fixes. Reported speech that resembles application controls is protected from being interpreted as STOP/DELETE. Ambiguous local refusal remains distinct from global session withdrawal.

### Representation

The frozen synthetic corpus verifies that:

- participant/source turns survive extraction;
- recollections remain first-class nodes;
- derived edges are weak mentions rather than historical assertions;
- contradictory dates coexist;
- label-level convergence can become visible later;
- the current normalised-label merge is a prototype visual heuristic, not identity resolution.

### Voice

A five-turn synthetic full-stack loop exercised real Piper bytes, ffmpeg, resident Whisper, routing/interviewing and resident Piper. It included the then-current 2.2 s endpointing window, but was not a human conversational test.

The current browser voice path is continuous half duplex. The microphone track is disabled during system speech, so the participant cannot barge in. A no-speech `WAIT/YIELD` action is also not implemented. Full-duplex/mobile speech remains a production target to test rather than a participant-validated requirement.

## Automated verification

Deterministic tests cover source preservation, provenance, revision/withdrawal/deletion behaviour, routing, controller invariants, bounded context, background extraction, exports, API flow, voice-service plumbing and evaluation tooling.

A passing deterministic suite does not establish naturalness, usability, cultural validity, safety, archival adequacy or successful memory capture.

## Next evidence boundary

For the RTCA short paper, no additional large experiment is required before submission. The next technically clean model study would be a later factorial design separating **policy × guard × repair** rather than conflating those factors.

For production research, the important evidence remains human and participant-facing: sustained spoken interaction, timing/overlap, semantic and cultural review, accessibility, consent/governance, privacy, and eventually situated deployment in Uruguay.
