# Prototype test report

**Updated:** 13 August 2026  
**Status:** tomorrow-demo implementation mechanically verified; current local-model scenario, routing and synthetic end-to-end voice checks completed; sustained human browser voice testing remains pending.
**Participant evidence:** none. All current scenarios are researcher-authored/synthetic.

This report records actual evidence and observed failures. Design requirements derived from the evidence are maintained separately in [`DESIGN-FOUNDATIONS.md`](DESIGN-FOUNDATIONS.md), [`COLLECTIVE-MEMORY-CAPTURE.md`](COLLECTIVE-MEMORY-CAPTURE.md), [`FUTURE-ARCHITECTURE.md`](FUTURE-ARCHITECTURE.md), and [`EVALUATION-FRAMEWORK.md`](EVALUATION-FRAMEWORK.md).

## Tomorrow-ready rehearsal — 13 August 2026

The current code was tested on the target laptop with `qwen3:30b-a3b-instruct-2507-q4_K_M`, resident Whisper and resident Piper.

- **Deterministic suite:** 109 tests passed, including ephemeral storage/audio cleanup, run isolation, source-only staged fields, participant controls without fabricated transcript, idempotent recorded example, protocol answers and late-extraction/transcription cleanup races.
- **Frozen corpus:** 10 intended synthetic conversations, 68 nodes, 74 relations, `Tito` in three conversations, and one contradictory chronology retained separately with sources.
- **Single-turn conversation set:** all 11 researcher-authored cases returned short, grounded replies. An unresolved `lo vimos` initially produced a presuppositional question; the policy and guard were tightened and the rerun yielded the floor instead. A later correction remains conversationally acceptable but still deserves human review.
- **Multi-turn rhythm set:** 12 turns across three four-turn conversations; four backchannels, seven invitations to continue and one grounded follow-up. No packed question, affirming `sí/claro`, therapeutic completion or direct-access question after hearsay passed the current guard.
- **Adversarial routing:** 49 cases, 46 exact and 48 acceptable, with no critical failure. The one non-acceptable case was the explicitly ambiguous `No quiero hablar de eso.`, classified as `PAUSE`; it does not end the session. A real critical failure on `Sí, dale, seguime preguntando` was found and fixed deterministically before this final run.
- **Synthetic voice loop:** five complete turns through real Piper bytes → ffmpeg → resident Whisper → router/interviewer → resident Piper. Resident ASR/TTS were used on every turn. Median stages were 43 ms conversion, 429 ms ASR, 645 ms routing, 1039 ms interviewing and 114 ms TTS; calculated median perceived reply was 4483 ms including the 2200 ms silence window.
- **Cleanup:** a race allowed late background extraction to resurrect a just-deleted in-memory run. A storage tombstone was added; the real two-turn voice path then cleaned to a 404 session, no persistent JSON and no remaining run id under `data/` or `demo/`.

This is researcher-authored/synthetic evidence, not participant validation. The in-app browser was unavailable to the implementation environment, so visual smoke testing at meeting resolution and a human 10–15-turn microphone rehearsal remain manual morning gates.

## Conversational-move rhythm smoke check — 12 August 2026

The first constrained controller over-specified surface language: every allowed action required a question and every acknowledgement was rewritten as `Te sigo`. That controller result is superseded.

The router and deterministic off-topic/participant-control barrier remain, while the interviewer now emits one complete utterance tagged as:

- `BACKCHANNEL`;
- `INVITE_CONTINUE`;
- `FOLLOW_UP`;
- `CLARIFY`;
- `ACKNOWLEDGE`.

Every accepted model move is grounded in the latest participant source turn. Questions are required only for follow-up/clarification.

The revised controller was exercised against `qwen3:30b-a3b-instruct-2507-q4_K_M` over Ollama using the three scripted four-turn conversations in `evaluation/rhythm-scenarios.json`:

- 12 assistant replies total;
- one reply contained a question;
- move distribution: five `ACKNOWLEDGE`, four `BACKCHANNEL`, one `FOLLOW_UP`, and two `INVITE_CONTINUE` fallbacks;
- ten model utterances passed the guard unchanged;
- `Entendido.` was rejected because an acknowledgement must ground in concrete participant content;
- `Contame cómo era esa bolsa.` was rejected because a content-directed prompt cannot be labelled as a floor-yielding invitation;
- fallback selection did not repeat a recent assistant phrase.

This run confirms that the controller no longer forces acknowledgement-plus-question cadence. It does not establish naturalness.

One accepted acknowledgement said the mother `recordaba bien`, a stronger inference than the participant's hearsay warranted, and the single follow-up (`¿Qué tipo de ruido era, el de la radio?`) remained stylistically awkward. Those findings motivated the current guard against certainty-hardening over uncertain/hearsay material.

## First live local-model check — 12 August 2026

An informal conversational check was executed on the target machine.

- **Model:** `qwen3:30b-a3b-instruct-2507-q4_K_M` (Ollama, Q4_K_M, 18.56 GB)
- **Endpoint:** `http://127.0.0.1:11434/v1/chat/completions`, unauthenticated, local
- **Sampling:** `temperature 0.7`, `top_p 0.8`, `max_tokens 256`
- **Extent:** one four-turn conversation plus one single-turn scenario check
- **Not done in this run:** the complete executable scenario set, repeated runs/scoring, full runtime benchmark, or voice round trip

No `<think>` content leaked into the transcript, confirming that the tested `2507-Instruct` deployment behaved as a non-thinking conversational model over the configured endpoint. The previously pulled `qwen3:30b` alias is a different hybrid-thinking deployment and should not be treated as equivalent evidence.

### What went well

- Held an approximate date without demanding an exact one or computing a birth year.
- Accepted a correction of place several turns later without arguing or erasing.
- Followed the topic the participant offered after a refusal instead of returning to the declined subject.
- Turns were short.

### Observed failures

1. **Presuppositional follow-up after hearsay disclaimer.** The participant said *«Del Flaco yo no me acuerdo. Lo que sé es porque mi vieja contaba…»* and the model asked *«¿Y cómo te sonaba él, cuando hablaba con tu tío?»* This assumed direct experience the participant had just disclaimed.
2. **Stilted acknowledgement.** After a refusal it replied *«Acepto.»*, which reads as a form response rather than ordinary Uruguayan conversation.
3. **Repetitive question frame.** Three of four turns used *«¿Y cómo era/eran…?»*.

The interaction policy was revised in response.

### Re-test after that policy revision

The same material was run again. The result was partial rather than a clean fix.

Resolved in that check:

1. the presupposition after hearsay disappeared; the model attributed to what the mother said rather than asking for direct participant perception;
2. the `Acepto.` acknowledgement disappeared and the model followed the participant-offered topic directly.

Not resolved/newly exposed:

- repeated echo/reformulation of participant wording became a new formula;
- two turns packed paired questions into one intervention despite an existing instruction not to do this;
- automatic reformulation risked hardening uncertain memory by restating it more flatly.

The important methodological finding is that adding prompt prohibitions did not produce proportional compliance; relieving one failure mode surfaced others. This is why the project now combines model policy with structural routing/guards and human review rather than treating prompt text as the safety mechanism.

The current policy/guard has changed further since these observations and has not yet been re-tested through a sustained human conversation. Do not report these older outputs as evidence that the current policy is now successful.

## Extraction check

Model extraction over the four participant turns produced eleven provisional items with correct source-turn references and preserved the participant's exact wording. It correctly typed hearsay, uncertainty and correction.

It mis-typed the refusal *«De la detención no quiero hablar»* as `uncertainty` rather than a refusal; there is currently no refusal type in the extraction vocabulary. This was withdrawn with a reason during the check, demonstrating why the audit/revision layer matters.

A defect was found and fixed during this run: extraction inherited the conversational `max_tokens=256` cap and truncated its JSON mid-string. Conversation and analysis now have separate token budgets.

## Performance changes after the first live check

The prototype was subsequently revised to remove avoidable latency:

- optional small `LLM_ROUTER_MODEL` for turn classification;
- extraction defaults to the small router model when configured and may be overridden separately;
- background extraction is queued, waits for conversational quiet and can be pre-empted by a new conversational call;
- configured Ollama models are warmed/kept resident;
- one HTTP client is reused;
- interview working context is bounded;
- aggregate field/chronology views are cached;
- browser field updates use server-sent change events rather than timed polling bursts;
- resident `whisper-server` can keep ASR weights loaded across turns;
- the microphone stream/analyser are retained across continuous half-duplex turns;
- current endpointing defaults to 2.2 seconds of detected silence and is configurable;
- turn/voice stages expose latency timings.

These implementation changes are mechanically covered where deterministic. Their actual end-to-end perceptual benefit still needs to be measured in the target spoken interaction.

## Automated verification

The local deterministic suite currently passes 109 tests. The GitHub Actions workflow verifies Python/browser syntax and pytest coverage including:

- transcript/source preservation;
- model/researcher provenance;
- revision/withdrawal/deletion behaviour;
- correction relations;
- exports;
- interaction-policy and guard invariants;
- local unauthenticated model configuration;
- router/extraction model separation;
- resident HTTP-client behaviour;
- bounded interviewer history;
- quoted control speech;
- extraction/conversation gating and pre-emption;
- cached aggregate views;
- API flow;
- mocked resident-Whisper request handling;
- evaluation-runner/tooling integrity.

Mechanical passing does not establish naturalness, usability, cultural validity, safety or memory-capture efficacy.

## Executable and manual scenario sets

`evaluation/scenarios.json` currently contains **11 executable researcher-authored conversational scenarios**:

1. uncertain date;
2. hearsay;
3. later correction;
4. refusal/redirection;
5. digression;
6. ambiguous local reference;
7. natural voseo;
8. contradiction;
9. emotionally charged memory;
10. participant-led topic return;
11. reported speech that resembles a control instruction.

Application-level off-topic/prompt-injection and participant-control checks are exercised separately because they should bypass the interviewer model.

`docs/MANUAL-TESTS.md` has now been expanded beyond the executable corpus with additional research-derived cases for:

- suggestion resistance;
- affirmation resistance;
- multiple-question packing;
- premature closure;
- participant correction of an interviewer error;
- archive blindness/cross-session leakage;
- deferred collective significance;
- derived-summary preservation.

These additions are requirements for the next evaluation pass. They have not yet produced evidence.

## Current prototype views

### Conversation

**Contribuir** is now the default participant-facing mode, with no aggregate graph visible. Current capabilities include:

- exact participant-turn preservation;
- local/hosted OpenAI-compatible live model integration;
- natural-Uruguayan-Spanish policy;
- participant-led framing rather than fixed questionnaire;
- structural separation of testimony, participant controls and off-topic commands;
- preservation of a participant turn when model generation fails.

### Campo de memoria

**Explorar el corpus** is now a deliberate, separately labelled researcher mode. The earlier on-screen `Mesa de trabajo` was removed. Manual annotation/derived operations remain in the API/data model/exports, but the second interface view is now the accumulated memory field.

The field:

- represents recollections as first-class nodes;
- attaches provisional extraction to exact recollections;
- uses weak `menciona` relations;
- retains disagreement;
- makes interpretation arrive after preservation;
- exposes source wording through node inspection;
- feeds a chronology view without first resolving contradictory dates.

Prototype limitation: extracted nodes with the same conservatively normalised label converge visually. This is possible label-level convergence, not production identity resolution and not evidence that two mentions necessarily refer to the same historical entity.

The `campo de memoria` should not be described as collective memory itself.

## Voice status

The browser voice path is implemented as continuous local half duplex:

```text
microphone → configurable 2.2 s endpointing heuristic → ffmpeg → resident whisper.cpp where configured
→ router/interviewer → Piper → speakers → microphone again
```

The microphone stream/analyser remain allocated; the track is disabled during system speech. The participant cannot barge in.

The synthetic diagnostic now exercises real audio through Whisper, model and Piper, but not a human microphone, browser playback onset or reflective pauses. Human voice interaction remains the largest empirical gap.

Required next check:

- one real 10–15-turn spoken conversation;
- ordinary reflective pauses and self-restarts;
- ASR errors on names, nicknames, places and dates;
- endpointing cuts;
- VAD/ASR/router/interviewer timings;
- TTS timing when instrumented;
- moments when half duplex prevents a natural interruption.

Production is intended to be mobile-first and full duplex. The current voice implementation is evidence-gathering infrastructure, not the final interaction architecture.

## Design requirements exposed by implementation and research

The consolidated requirements are maintained in the long-lived design docs rather than duplicated exhaustively here. The most important are:

1. The project objective is collective-memory capture, not an interviewer benchmark.
2. Preserve contribution before requiring successful interpretation.
3. Participant source, machine mediation and derived interpretation remain distinguishable.
4. For voice, original audio is source and ASR text is a machine-derived representation.
5. Generated testimony is prohibited in the participant source layer.
6. Corrections/qualifications do not destructively replace earlier source.
7. The live interviewer is session-local and archive-blind by default.
8. Not pursued in the current dialogue does not imply discarded or historically insignificant.
9. Historical significance may emerge only across later contributions; immediate relevance selection must therefore not become irreversible filtering.
10. Production needs participant-owned local refusal, protocol/consent information, scoped consent, relational privacy, differentiated access and a threat model.
11. Production cross-session identity linking must be provisional and provenance-bearing rather than silent string merging.
12. Mobile full-duplex speech is the intended participant interaction direction; participant interruption should be easy and system interruption conservative.

## Next evidence gate

1. Run sustained human/researcher conversation against the current policy/guard, not the superseded one recorded above.
2. Run the real 10–15-turn browser voice conversation with resident Whisper confirmed and a deliberate 1.8-second hesitation.
3. Complete the visual smoke test at meeting resolution.
4. Run the expanded manual suggestion/affirmation/archive-blindness cases, retaining representative failures.
5. Use these results to decide the next prototype/production architecture rather than treating the current code as the starting point by default.
