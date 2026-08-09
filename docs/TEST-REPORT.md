# Prototype test report

**Status:** implementation complete and mechanically verified; live-model Uruguayan-Spanish interaction tests remain the final evidence gate.

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
