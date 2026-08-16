# Status

**Date:** 16 August 2026  
**Phase:** disposable interaction prototype plus production-design research  
**Participant data:** none; current experiments use researcher-authored synthetic material  
**RTCA evidence:** Level 0, B1 multi-model comparison, guard-effect audit, B2 repair experiment and streaming TTFT replication completed

## Project objective

The central design problem is to capture dispersed, partial and situated recollections connected to Uruguay's detained-disappeared without forcing contributors to arrive with a finished testimony or translating their memories into database categories before they can speak. The conversational agent, provenance model, memory field and technical architecture are means to that end.

The repository deliberately separates the current disposable prototype from long-lived production guidance. The prototype is an experimental instrument, not a production architecture.

The long-lived **Capturing Collective Memories of the Disappeared with Artificial Intelligence** project is being developed toward a **speech-first, full-duplex voice interface**. The production design is intended to let participants interrupt easily, continue through apparent turn boundaries, overlap naturally and correct an incorrect system intervention before it finishes. The current half-duplex browser path is only a disposable test instrument and must not be mistaken for the target interaction model.

## Current prototype

The implementation currently provides:

- separate participant capture and researcher corpus-exploration modes;
- participant turns preserved before interpretation;
- model interventions retained as a distinct attributable layer;
- recollections as first-class nodes with weak `menciona` relations;
- contradictory dates, hearsay, uncertainty and correction retained rather than silently resolved;
- provisional cross-conversation convergence through conservatively normalised labels, explicitly not identity resolution;
- a constrained interviewer with `BACKCHANNEL`, `INVITE_CONTINUE`, `FOLLOW_UP`, `CLARIFY`, and `ACKNOWLEDGE` moves;
- a deterministic intervention-admission guard checking structural/lexical source relations, repeated wording, question packing and selected forms of unsupported certainty;
- optional local continuous half-duplex voice with a configurable 2.2 s endpointing heuristic;
- no implemented no-speech `WAIT/YIELD` action and no production full-duplex speech path yet;
- deterministic tests and frozen researcher-authored evaluation tooling.

The `campo de memoria` exposes relations among stored acts of recollection. It is not claimed to be collective memory itself, and same-label convergence is not historical corroboration or identity resolution.

## Executed RTCA evaluation

### Level 0

The frozen deferred-significance invariant suite passed **16/16** checks:

- 5/5 delayed cross-session convergence checks;
- 3/3 non-collapse checks;
- 8/8 controller/guard probes.

These are mechanical implementation properties, not evidence of interviewing quality or human-memory effects.

### B1

B1 executed three researcher-authored intervention systems across five scenario families, five stochastic repetitions and three local models: **225/225 decisions completed with no request failures**.

The delivered-surface structural screen marked possibility preservation in 29/75 immediate-information cases, 37/75 adaptive semi-structured cases and 71/75 deferred-significance cases. This is not a clean policy comparison: only the deferred condition used the deterministic admission guard, and the screen measures several structures the guard itself rejects.

The guard-path audit exposed the more important result. Deferred-significance fallback rates were:

- Qwen3-30B-A3B: **25/25 (100%)**;
- Qwen3-4B: **20/25 (80%)**;
- Mistral Small 3.2: **18/25 (72%)**.

A system can satisfy structural restraint by ceasing to be a useful interviewer.

### B2

B2 retained the same model panel and five scenario families, but allowed up to two guard-aware regenerations after a rejected proposal. It completed **75/75 decisions**.

Final deterministic fallback fell to:

- Qwen3-30B-A3B: **4%**;
- Qwen3-4B: **20%**;
- Mistral Small 3.2: **8%**.

That did not turn repair into successful elicitation. Qwen3-30B reached admission mostly through minimal backchannels; Mistral remained dominated by minimal acknowledgements/backchannels; Qwen3-4B produced more active probes but repeatedly misread the Rioplatense expression `caía por el bar` while satisfying the structural/lexical admission checks. Lexical overlap is not semantic fidelity.

B2 also makes the real-time cost visible. Median accumulated sequential model-request time was 2.51 s for Qwen3-30B, 1.93 s for Qwen3-4B and 7.09 s for Mistral. Among models with both first-pass and repaired acceptances, the median rose from 0.80 to 1.99 s for Qwen3-4B and from 3.20 to 7.31 s for Mistral. These are local request times, not streaming TTFT or participant-perceived speech latency. See `evaluation/results/rtca-experiment-b2-20260815T050113Z/LATENCY-AUDIT.md`.

The combined experimental result is diagnostic rather than a leaderboard: tightening epistemic restraint can move the interviewer among informational injection, deterministic fallback, interactional minimalism, semantically distorted but structurally admissible probing, and delay.

The formal `human_*` adjudication fields remain unfilled. Do not report quantitative rates for useful facilitation, semantic distortion, informational noise, cultural validity, trauma-informed adequacy or participant benefit from these experiments.

### B2 streaming TTFT replication

The independent streaming replication completed **75/75 decisions** and is committed under:

`evaluation/results/rtca-experiment-b2-ttft-20260816T025921Z/`

Result commit: `df6e2a00e7cc1af8756c7e3c01f65ecfa3a71bb2`.

The run retained the same five B2 scenarios, three-model panel and guard-aware repair design, while enabling OpenAI-compatible streaming. It used one excluded warm-up request per model.

Runtime provenance:

- Apple M1 Max / 64 GB unified memory;
- Ollama server **0.32.5**;
- Ollama client **0.32.9**;
- CLI version-mismatch warning retained in the manifest.

First-attempt TTFT median/p90:

- Qwen3-30B-A3B: **164 / 347 ms**;
- Qwen3-4B: **205 / 476 ms**;
- Mistral Small 3.2: **252 / 613 ms**.

Admission-ready median/p90, i.e. earliest safe delivery under the current completed-candidate guard:

- Qwen3-30B-A3B: **1.755 / 1.938 s**;
- Qwen3-4B: **1.365 / 2.447 s**;
- Mistral Small 3.2: **4.084 / 6.008 s**.

Median admission-ready time is approximately 10.7×, 6.6× and 16.2× first-attempt TTFT respectively.

The central result is:

> **model TTFT is not equivalent to safe conversational response onset when admission control requires the completed candidate.**

For the primary model, content begins streaming at 164 ms median but the intervention is not admission-ready until 1.755 s median. The guard validates complete JSON, and rejected candidates must finish before repair begins. Simply streaming generated tokens into TTS would therefore bypass the intervention-admission mechanism.

The replication is stochastic and is not pooled with original B2. Its fallback counts were 1/25, 6/25 and 4/25, compared with original B2 counts 1/25, 5/25 and 2/25. Original B2 remains the canonical behavioural/qualitative run; this replication supplies streaming timing evidence.

Full audit: `evaluation/results/rtca-experiment-b2-ttft-20260816T025921Z/TTFT-AUDIT.md`.

## Current production questions

The experimental failures sharpen rather than settle the production design. Open questions include:

- whether a no-speech `WAIT/YIELD` action is preferable to computationally generated backchannels in some moments;
- how admission can become compatible with token streaming without exposing an intervention before its epistemic constraints have been checked;
- how to ground interventions in source spans broader than the latest turn without allowing unsupported reconstruction;
- how to replace brittle lexical admission tests with semantics that remain auditable;
- how to support participant interruption and overlap without converting speech timing into another source of pressure;
- how to separate capture, archive, access and research layers while preserving withdrawal, provenance and relational privacy;
- how to govern provisional cross-session identity/coreference hypotheses;
- what human and participant evidence is required before any production deployment.

Full duplex is the production interaction direction, but its participant benefits and appropriate timing policy remain empirical questions to test rather than established outcomes.

## Repository boundaries

- Implementation, frozen technical evidence and production-design documentation: this repository.
- Private manuscripts and publication research: `krahd/research`.
- Global cross-repository status and calendar: `krahd/tom-work-admin`.

Public documentation should not depend on links into private research repositories. Primary public references and self-contained implementation evidence should be used where reproducibility matters.
