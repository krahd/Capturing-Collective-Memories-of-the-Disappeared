# Current implementation goal

Implement and test the disposable two-view prototype described in `PROTOTYPE.md`.

The prototype consists of:

1. **Conversation view** — a sustained, natural, participant-led conversational interaction designed for adult native speakers of Uruguayan Spanish.
2. **Conversation workbench** — an apparatus for inspecting and working on the conversation itself: selection, annotation, uncertainty/hearsay/correction/withdrawal status, provisional entity/event/theme extraction, source-turn traceability, correction links, editing, and export.

## Definition of done

The goal is done when:

- the prototype runs locally from documented setup instructions;
- the conversation can sustain realistic multi-turn exchanges in natural Uruguayan Spanish without becoming a questionnaire;
- the interaction follows digressions, corrections, refusals, uncertainty, and topic returns plausibly;
- the transcript is preserved exactly;
- derived material remains explicitly provisional, editable, and traceable to source turns;
- the workbench supports the core inspection and annotation operations;
- sessions export to JSON and Markdown;
- deterministic behaviour has automated tests;
- a documented manual test suite includes several researcher-authored Uruguayan-Spanish scenarios;
- the test round produces a concrete list of interaction and architectural requirements for the eventual production system.

The prototype code is disposable. No architectural decision in this phase is presumed to survive into the production system.
