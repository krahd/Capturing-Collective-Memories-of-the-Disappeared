# Status

**Date:** 15 August 2026  
**Phase:** disposable interaction prototype plus production-design research  
**Participant data:** none; current experiments use researcher-authored synthetic material  
**RTCA evidence:** Level 0, B1 multi-model comparison, guard-effect audit and B2 repair experiment completed; streaming TTFT replication instrumented and pending execution on the target machine

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

### B2 TTFT replication

A new runner, `scripts/run_rtca_ttft_experiment.py`, now reproduces the B2 scenario/model/policy/repair design using OpenAI-compatible streaming so that **time to first token** can be measured directly. The frozen B2 results are not modified.

The replication records, per attempt:

- model TTFT: request dispatch to first non-empty streamed content chunk;
- full candidate completion time;
- first-token time relative to the start of a repaired decision;
- guard outcome and complete reassembled candidate.

It also records **admission-ready time**. This distinction matters because the current deterministic guard validates a completed JSON candidate. The first streamed model token cannot yet be exposed safely to the participant; the architecture does not know whether the intervention is admissible until generation completes. Consequently:

> **model TTFT is not equivalent to safe conversational response onset when admission control requires the completed candidate.**

Each model receives one excluded streaming warm-up request so measured TTFT characterises resident-model behaviour rather than first-load time.

Current target-machine Ollama versions supplied for the replication:

- server: **0.32.5**;
- client: **0.32.9** (the CLI reports the server/client mismatch warning).

Protocol: `evaluation/EXPERIMENT-B2-TTFT-PROTOCOL.md`.

The runner and streaming parser have CI coverage. The implementation CI passed after adding the TTFT instrumentation. The actual 75-decision model run must execute on the target machine hosting the frozen Ollama model panel; it cannot be produced by GitHub-hosted CI.

## Current production questions

The experimental failures sharpen rather than settle the production design. Open questions include:

- whether a no-speech `WAIT/YIELD` action is preferable to computationally generated backchannels in some moments;
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
