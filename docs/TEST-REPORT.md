# Prototype test report

**Status:** implementation complete and mechanically verified; live-model Uruguayan-Spanish interaction tests remain the final evidence gate.

## Automated verification

GitHub Actions verification on 8 August 2026, commit `5c96169e62279276fa7f783bc1daeafe6f1ab7c4`, completed successfully with:

- `python -m py_compile app.py model.py state.py`;
- `node --check static/app.js`;
- `pytest -q`: **11 passed in 0.43 s**, with no pytest warnings.

The automated suite covers:

- exact transcript persistence and JSON round-trip;
- mandatory source-turn traceability for annotations and derived items;
- correction relations that preserve both the earlier and later record;
- editing derived material without mutating transcript text;
- deleting provisional derived material without changing source turns, while removing relations that would otherwise dangle;
- Markdown export with source ids and provisional-material warning;
- explicit conversational-policy requirements for Uruguayan Spanish, non-questionnaire behaviour, digression, uncertainty, and fact-checking refusal;
- an end-to-end API flow with a deterministic fake conversational model, including annotation, derivation, export, and derived-item deletion.

Earlier local verification also included a live FastAPI smoke test for configuration and session creation.

## Implemented prototype

The disposable prototype now provides the two intended coordinated views.

### Conversation

- exact participant-turn preservation;
- OpenAI-compatible live model integration through environment configuration;
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

The repository contains ten researcher-authored scenarios in `docs/MANUAL-TESTS.md`. These must be run against the actual intended prototype model and assessed by a competent Uruguayan-Spanish reader. A language model cannot be declared natural or usable for Uruguayan native speakers from prompt inspection or deterministic software tests alone.

No model credential is available in the current execution environment, so that experiment has not been fabricated. Until the test round is recorded here, the correct description is **implemented, runnable, and mechanically verified**, not “validated with Uruguayan speakers”.

## Requirements already exposed by implementation

1. The production system must separate immutable/raw conversational turns from editable derived interpretation.
2. Every derived interpretation needs explicit source-turn provenance.
3. Correction cannot be implemented as destructive replacement; both utterances and the relation between them matter.
4. Model failure must not discard a participant turn.
5. Conversational orchestration and post-conversation analysis are distinct operations even if the prototype uses the same model provider.
6. Participant language should remain untouched in the transcript; normalisation belongs, if anywhere, in a derived and revisable layer.
7. Provisional interpretation must be genuinely disposable: deleting it cannot damage the transcript or leave invalid structural references.
8. Model/provider configuration should remain replaceable until interaction tests identify concrete latency and language-quality requirements.
9. Production consent, authentication, archival stewardship, access control, and security cannot be inferred from this prototype and require separate design.

## Next evidence gate

Run all ten scenarios with the intended model, score them using the rubric, retain representative failures, revise the interaction policy only in response to observed failures, and repeat. After the interaction is stable enough for expert/researcher testing, design the production architecture from the resulting requirements rather than from this codebase.
