# Status

**Date:** 16 August 2026  
**Phase:** disposable interaction prototype plus production-design research  
**Participant data:** none; current experiments use researcher-authored synthetic material  
**RTCA evidence:** Level 0, B1 multi-model comparison, guard-effect audit, B2 repair experiment and clean streaming timing replication completed

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

That did not turn repair into successful elicitation. Qwen3-30B reached admission mostly through minimal backchannels; Mistral remained dominated by minimal acknowledgements/backchannels. The Rioplatense `place-bar` case exposes a different limitation: B1 unambiguously interprets `caía por el bar` as a physical fall, while all five Qwen3-4B B2 outputs target variants of `cómo caía por el bar` for clarification and drop the source hedge `creo` while passing structural/lexical admission. Lexical overlap is not semantic or epistemic fidelity.

B2 also makes the real-time cost visible. Median accumulated sequential model-request time was 2.51 s for Qwen3-30B, 1.93 s for Qwen3-4B and 7.09 s for Mistral. Among models with both first-pass and repaired acceptances, the median rose from 0.80 to 1.99 s for Qwen3-4B and from 3.20 to 7.31 s for Mistral. These are local request times, not streaming onset or participant-perceived speech latency. See `evaluation/results/rtca-experiment-b2-20260815T050113Z/LATENCY-AUDIT.md`.

The formal `human_*` adjudication fields remain unfilled. Do not report quantitative rates for useful facilitation, semantic distortion, informational noise, cultural validity, trauma-informed adequacy or participant benefit from these experiments.

### Clean B2 streaming timing replication — canonical timing evidence

The clean fixed-seed streaming replication completed **75/75 decisions** and is stored under:

`evaluation/results/rtca-experiment-b2-ttft-clean-20260816T181115Z/`

Raw result commit: `1ec5442779ef842d23c01029d0427acd9c8b1303`.

Audit: `evaluation/results/rtca-experiment-b2-ttft-clean-20260816T181115Z/TTFT-CLEAN-AUDIT.md`.

Runtime controls:

- Apple M1 Max / 64 GB unified memory;
- Ollama server **0.32.9**;
- Ollama client **0.32.9**;
- dedicated local `ollama serve` process;
- explicit context length **8192** via `OLLAMA_CONTEXT_LENGTH`;
- fixed candidate-request seed schedule beginning at **42**;
- one excluded warm-up request per model.

Timing results:

| Model | First-attempt candidate-stream onset median / p90 | Accepted-candidate stream onset from decision start median / p90 | Admission-ready median / p90 | Fallback |
|---|---:|---:|---:|---:|
| Qwen3-30B-A3B | **166 / 352 ms** | **1,559 / 1,781 ms** | **1.771 / 1.988 s** | 0/25 |
| Qwen3-4B | **162 / 244 ms** | **801 / 937 ms** | **1.219 / 1.948 s** | 4/25 |
| Mistral Small 3.2 | **253 / 617 ms** | **2,565 / 4,845 ms** | **4.067 / 6.486 s** | 2/25 |

The primary-model sequence is therefore **166 ms first-attempt candidate-stream onset → 1.559 s accepted-candidate stream onset → 1.771 s admission-ready**. Across all three models, most of the median admission interval elapses before the accepted candidate stream begins.

The model returns a structured JSON candidate. The first non-empty streamed content chunk can precede the participant-facing `utterance` field, so both stream-onset measures are **lower bounds on participant-facing utterance onset**, not measurements of speech onset.

The clean run closely reproduces the earlier exploratory timing for Qwen3-30B and Mistral while removing the previous Ollama 0.32.5/0.32.9 mismatch. The earlier run remains preserved as provenance but is superseded for paper-facing timing.

The central timing result is:

> **Fast candidate-stream onset does not imply fast admissible speech when the architecture serially generates, rejects, repairs and validates complete candidates.**

The fixed-seed streaming run is not pooled with original B2. Original B2 remains canonical for behavioural/qualitative evidence; the clean run supplies canonical timing evidence.

## Evidence boundaries sharpened for the RTCA paper

The current paper treats later recurrence as a researcher-defined signal for retrospective scrutiny, not as historical verification, and distinguishes foreclosure-risk interventions from observed downstream effects. In the synthetic stress-test suite:

- all five convergence families recur;
- no matched non-recurring branches are present;
- later B/C sessions are withheld from generation;
- no subsequent participant turns are observed after the intervention.

The experiment therefore diagnoses intervention-risk mechanisms, guard/repair behaviour, semantic/epistemic failure and timing. It does not establish downstream effects on recollection.

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

Streaming safety moderation exists for generic harmful-content policies; the project-specific open question is whether epistemic interview constraints such as attribution, uncertainty preservation and semantic grounding can be checked incrementally without collapsing interaction.

Full duplex is the production interaction direction, but its participant benefits and appropriate timing policy remain empirical questions to test rather than established outcomes.

## Repository boundaries

- Implementation, frozen technical evidence and production-design documentation: this repository.
- Private manuscripts and publication research: `krahd/research`.
- Global cross-repository status and calendar: `krahd/tom-work-admin`.

Public documentation should not depend on links into private research repositories. Primary public references and self-contained implementation evidence should be used where reproducibility matters.
