# Status

**Date:** 8 August 2026  
**Phase:** disposable interaction prototype  
**Implementation:** complete  
**Mechanical verification:** passing  
**Live-model Uruguayan-Spanish evaluation:** pending

## Implemented

- two coordinated views: Conversation and Mesa de trabajo;
- OpenAI-compatible conversational model integration;
- interaction policy targeting natural adult Uruguayan/Rioplatense Spanish without caricature or questionnaire behaviour;
- exact turn-by-turn transcript preservation;
- annotations and uncertainty/hearsay/correction/withdrawal/significance labels;
- provisional manual and model-derived entities/events/places/times/themes with exact source-turn provenance;
- editable and deletable derived material without transcript mutation;
- correction/qualification/contradiction/reference relations;
- JSON and Markdown export;
- local JSON session persistence ignored by git;
- automated CI verification.

## Verification

GitHub Actions run for commit `5c96169e62279276fa7f783bc1daeafe6f1ab7c4` passed:

- Python compilation;
- JavaScript syntax validation;
- 11 automated tests, all passing, no pytest warnings.

The test suite covers transcript preservation, source traceability, derived editing/deletion, correction relations, export, policy invariants, and an end-to-end API flow using a deterministic fake model.

## Remaining goal gate

The prototype has not yet been evaluated with the intended live language model because no model credential is available in the current execution environment. `docs/MANUAL-TESTS.md` defines ten researcher-authored Uruguayan-Spanish scenarios and a scoring rubric.

Issue #1 remains open until those conversations are actually run and reviewed. This is an evidence boundary, not an implementation blocker.

## After the prototype test round

Do not incrementally harden this code into the production system by default. Use the observed interaction failures and successful operations to design the actual architecture from first principles.
