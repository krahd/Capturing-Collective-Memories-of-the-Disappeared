# Prototype test report

**Status:** implementation complete and mechanically verified. A first informal
live-model check has been run; the full ten-scenario scored protocol has **not**
been run and remains the final evidence gate.

## First live local-model check — 12 August 2026

The first actual conversational exchange with a local model was executed on the
target machine. This is an informal check, not the scored protocol.

- **Model:** `qwen3:30b-a3b-instruct-2507-q4_K_M` (Ollama, Q4_K_M, 18.56 GB)
- **Endpoint:** `http://127.0.0.1:11434/v1/chat/completions`, unauthenticated, local
- **Sampling:** `temperature 0.7`, `top_p 0.8`, `max_tokens 256`
- **Extent:** one four-turn conversation plus one single-turn scenario check
- **Not done:** the ten scenarios, repetitions, scoring against the rubric, and
  any runtime/TTFT measurement

No `<think>` content leaked into the transcript, confirming that the
`2507-Instruct` build behaves as a non-thinking conversational model over the
OpenAI-compatible endpoint. The previously pulled `qwen3:30b` alias is the
hybrid-thinking variant and should not be used for conversational runs.

### What went well

- Held the approximate date without asking for an exact one or computing a birth year.
- Accepted a correction of place several turns later without arguing or erasing.
- Followed the topic the participant offered after a refusal instead of returning
  to the declined subject.
- Turns were short, with a single question.

### Observed failures

1. **Presuppositional follow-up after a hearsay disclaimer.** The participant said
   *«Del Flaco yo no me acuerdo. Lo que sé es porque mi vieja contaba…»* and the
   model asked *«¿Y cómo te sonaba él, cuando hablaba con tu tío?»*, which assumes
   direct experience the participant had just disclaimed. This fails **no
   conducción** and **incertidumbre**.
2. **Stilted acknowledgement.** After the refusal it replied *«Acepto.»*, which
   reads as a form response rather than Uruguayan conversation. Fails **naturalidad**.
3. **Repetitive question frame.** Three of four turns used *«¿Y cómo era/eran…?»*.
   Fails **economía** and reads as a script.

The interaction policy in `model.py` was revised in direct response to these three
observations. The observations above describe the pre-revision policy.

### Re-test after the policy revision

The same material was run again against the revised policy. The result is partial
and should not be read as a fix.

Resolved:

1. **Presupposition after hearsay** — resolved. The model now attributes to the
   declared source: *«¿alguna vez te contó por qué venía, o cómo era cuando
   estaba?»* asks what the mother said rather than what the participant witnessed.
2. **Stilted acknowledgement** — resolved. It moves directly to the topic the
   participant offered, with no "Acepto"-style acknowledgement.

Not resolved, and newly introduced:

- **Repetitive frame** — not resolved, only changed shape. It now opens turns by
  echoing the participant's own words (*«Al fondo a jugar…»*, *«Las reuniones en
  casa de tu abuela…»*) as a repeated formula.
- **New: paired questions.** Two of three turns asked two questions at once
  (*«¿por qué venía, o cómo era cuando estaba?»*), which the policy already
  prohibits. Adding prohibitions did not increase compliance with an existing one.
- **New: automatic reformulation.** The echo opening is the reformulation the
  policy explicitly warns against, and it risks hardening an uncertain memory by
  restating it.

This is the central methodological finding so far: **adding rules to the policy
did not produce proportional compliance, and relieving one failure mode surfaced
others.** Whether that is a limit of prompt-level control at this model scale, or
of this policy's formulation, is exactly what the scored protocol should
establish. Native-speaker judgement of Uruguayan naturalness remains outside what
the automated harness can decide.

### Extraction check

Model extraction over the four participant turns produced eleven provisional
items with correct source-turn references and preserved the participant's exact
wording. It correctly typed hearsay, uncertainty and the correction. It
mis-typed the refusal *«De la detención no quiero hablar»* as `uncertainty`
rather than a refusal; there is currently no refusal type in the extraction
vocabulary. This was withdrawn with a reason during the check, which is the
behaviour the audit layer exists to make possible.

A defect was found and fixed during this run: extraction inherited the
conversational `max_tokens=256` cap and truncated its JSON mid-string, so
extraction silently produced nothing. Conversation and analysis now have separate
token budgets.

## Automated verification

The repository's GitHub Actions workflow verifies:

- Python compilation for the prototype;
- browser JavaScript syntax;
- deterministic pytest coverage of transcript preservation, provenance, correction relations, editable derived material, exports, interaction-policy invariants, configuration, and the end-to-end API flow.

On 9 August 2026 the model connector was revised so that an API key is required for the default OpenAI endpoint but not for unauthenticated local OpenAI-compatible servers. The corresponding configuration tests are included in the deterministic suite.

A reproducible live-evaluation harness was also added. Its tests verify that the ten researcher-authored scenarios are machine-readable and that the runner itself starts without requiring credentials.

## Implemented prototype

The disposable prototype provides the two intended coordinated views.

### Conversation

- exact participant-turn preservation;
- OpenAI-compatible live model integration through environment configuration;
- direct use of authenticated hosted or unauthenticated local OpenAI-compatible endpoints;
- a dedicated Uruguayan-Spanish interaction policy;
- participant-led conversational framing rather than a fixed questionnaire;
- preservation of a participant turn even when model generation fails.

### Mesa de trabajo

- turn selection;
- annotations and uncertainty/hearsay/correction/withdrawal/significance labels;
- manually created provisional entities/events/places/times/themes and other derived material;
- optional model extraction linked to exact source turns;
- editing and deletion of provisional derived material without changing the transcript;
- relations such as `corrects`, `qualifies`, and `contradicts`;
- JSON and readable Markdown export with provenance.

## Live conversational validation

`docs/MANUAL-TESTS.md` defines ten researcher-authored scenarios. Their executable counterparts are stored in `evaluation/scenarios.json` and can be run against the configured model with:

```bash
python scripts/run_live_scenarios.py
```

The runner records raw model responses and complete HTTP round-trip latency under ignored local files in `evaluation/results/`. It does not judge the responses automatically. Conversational quality must be reviewed using the human-authored rubric in `docs/MANUAL-TESTS.md`.

The recorded `round_trip_ms` value is not time to first token. The current disposable prototype uses a non-streaming request and therefore cannot by itself establish TTFT, warm-prefix behaviour, interruption handling, server-side cancellation, or duplex turn-taking. Those runtime properties should be measured independently with Modelito's local conversational benchmark on the target machine.

The previous absence of a hosted-model credential is no longer the main blocker: the prototype can now be pointed directly at an unauthenticated local OpenAI-compatible runtime. No target-runtime/model run has yet been recorded in this repository, so that experiment must not be retroactively inferred from mechanical tests.

Until the test round is recorded, the correct description is **implemented, runnable, mechanically verified, and ready for live local-model evaluation**, not “validated with Uruguayan speakers”.

## Evaluation protocol for the RTCA submission

The RTCA evidence should be kept in two distinct layers.

### Conversational layer

For each of the ten scenarios, retain the exact model output and manually score 0–2 on:

- seguimiento;
- naturalidad;
- no conducción;
- incertidumbre;
- agencia;
- economía.

A response should not be treated as passing when it receives a zero in no conducción, incertidumbre, or agencia even if its aggregate score is high. Representative failures are more informative for the paper than an aggregate score without examples.

### Runtime layer

On the same target machine and with comparable model families/configuration where practical, record separately:

- first-request TTFT;
- warm-prefix TTFT across repeated conversational context;
- context-growth latency;
- first useful streamed phrase;
- decode tokens/s;
- cancellation/stream-close behaviour;
- approximate memory pressure, with the known limitations of process RSS on Apple unified memory.

This layer is intended to determine whether a runtime is suitable for sustained conversational interaction. It does not establish linguistic naturalness or epistemic adequacy.

## Requirements exposed by implementation

0. An interpretation must carry its author. Before the audit layer existed, a
   model-extracted item and a researcher-written item were indistinguishable in
   storage and on screen. Attribution is a representational requirement, not a
   logging convenience.
0b. Removal has at least two distinct meanings — *retirar* (retain, mark, keep the
   reason) and *eliminar* (destroy) — and a memory system must not collapse them.
   Purging also has to redact the text this system quoted about the item in its
   own record, otherwise "eliminar" is a false promise; that redaction must itself
   be recorded.
1. The production system must separate immutable/raw conversational turns from editable derived interpretation.
2. Every derived interpretation needs explicit source-turn provenance.
3. Correction cannot be implemented as destructive replacement; both utterances and the relation between them matter.
4. Model failure must not discard a participant turn.
5. Conversational orchestration and post-conversation analysis are distinct operations even if the prototype uses the same model provider.
6. Participant language should remain untouched in the transcript; normalisation belongs, if anywhere, in a derived and revisable layer.
7. Provisional interpretation must be genuinely disposable: deleting it cannot damage the transcript or leave invalid structural references.
8. Model/provider configuration should remain replaceable until interaction tests identify concrete latency and language-quality requirements.
9. Real-time optimisation is not automatically an epistemic good. A future voice system must not treat hesitation, silence, refusal, correction, or participant-led topic shifts merely as latency defects.
10. Production consent, authentication, archival stewardship, access control, ownership, security, and retention cannot be inferred from this prototype and require separate design.

## Next evidence gate

Run all ten scenarios with the intended local model, score them using the rubric, retain representative failures, revise the interaction policy only in response to observed failures, and repeat. Run the runtime benchmark separately. After the interaction is stable enough for expert/researcher testing, design the production architecture from the resulting requirements rather than from this codebase.
