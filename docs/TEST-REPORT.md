# Prototype test report

**Status:** 10 deterministic implementation tests completed locally; live-model Uruguayan-Spanish interaction tests pending a configured API key/model.

## Automated verification

The automated suite covers:

- exact transcript persistence and JSON round-trip;
- mandatory source-turn traceability for annotations and derived items;
- correction relations that preserve both the earlier and later record;
- editing derived material without mutating transcript text;
- Markdown export with source ids and provisional-material warning;
- explicit conversational-policy requirements for Uruguayan Spanish, non-questionnaire behaviour, digression, uncertainty, and fact-checking refusal;
- an end-to-end API flow with a deterministic fake conversational model.

Local verification on 8 August 2026 also included Python compilation, JavaScript syntax checking, and a live FastAPI smoke test for configuration and session creation.

## Live conversational validation

The repository contains ten manual scenarios in `docs/MANUAL-TESTS.md`. These must be run against the actual configured prototype model. A language model cannot be declared natural or usable for Uruguayan native speakers from prompt inspection alone.

Until that test round is recorded here, the implementation should be described as **working and testable**, not as validated with Uruguayan participants.

## Requirements already exposed by implementation

1. The production system must separate immutable/raw conversational turns from editable derived interpretation.
2. Every derived interpretation needs explicit source-turn provenance.
3. Correction cannot be implemented as destructive replacement; both utterances and the relation between them matter.
4. Model failure must not discard a participant turn.
5. Conversational orchestration and post-conversation analysis are distinct operations even if the prototype uses the same model provider.
6. Participant language should remain untouched in the transcript; normalisation belongs, if anywhere, in a derived and revisable layer.
7. Model/provider configuration should remain replaceable until interaction tests identify concrete latency and language-quality requirements.
8. Production consent, authentication, archival stewardship, access control, and security cannot be inferred from this prototype and require separate design.

## Next evidence gate

Run all ten scenarios with the intended model, score them using the rubric, retain representative failures, revise the prompt only in response to observed failures, and repeat. After the interaction is stable enough for expert/researcher testing, design the production architecture from the resulting requirements rather than from this codebase.
