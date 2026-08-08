# Disposable prototype plan

## Goal

Implement and test a working two-view prototype consisting of a **Conversation view** and a **Conversation workbench**. The prototype must support multi-turn conversations that sound natural and usable to adult native speakers of Uruguayan Spanish, while preserving the exact conversation and allowing the researcher to inspect, annotate, connect, revise, and export material derived from it.

This is a discovery prototype. Its code may be discarded completely after testing. Its purpose is to reveal interaction, conversational, representational, and architectural requirements for the eventual system.

### Goal completion criteria

The goal is complete only when all of the following are true:

1. The application runs end-to-end locally from documented setup instructions.
2. A participant can conduct a sustained multi-turn conversation in Uruguayan Spanish without the system collapsing into a scripted questionnaire.
3. The conversational register is recognisably appropriate for Uruguay: natural Rioplatense Spanish, appropriate voseo where context calls for it, locally plausible lexical and pragmatic choices, and no generic translated-English or caricatured regional phrasing.
4. The system follows what the participant actually says, asks contextually motivated follow-ups, tolerates digression, and can return to earlier material without mechanically repeating questions.
5. The system does not silently turn uncertainty, hearsay, contradiction, speculation, or correction into fact.
6. The participant can decline, redirect, correct, qualify, or stop a line of conversation without conversational friction.
7. The exact transcript is preserved turn by turn.
8. The workbench can select turns or passages, add editable annotations and statuses, connect later corrections to earlier statements, and create provisional entities/events/themes linked to exact source turns.
9. Automatically derived material is visibly distinct from participant speech and remains editable and traceable.
10. A session can be exported as machine-readable JSON and readable Markdown without requiring the application to inspect it.
11. The prototype passes automated functional tests for its deterministic components and a documented manual interaction test suite.
12. At least several researcher-authored Uruguayan-Spanish test conversations are completed and reviewed, producing a concrete list of requirements and failures for the production architecture.

## Purpose

Build the smallest working system that lets us experience and critique the intended interaction before designing the production architecture.

The prototype should answer:

- Can the conversational interaction sustain a natural memory-oriented exchange rather than behave like an interview form?
- Which kinds of follow-up feel useful, intrusive, leading, repetitive, or flattening?
- Which operations are needed to inspect, annotate, revise, connect, and export the conversation?
- What information must remain traceable to exact source turns?
- Which interaction failures should become explicit design requirements for the final system?

## Proposed first prototype

A local web application with two coordinated views.

### Conversation view

A chat-like interface for a participant/researcher test conversation. The language model receives a compact interaction policy oriented toward attentive, non-leading memory elicitation.

The conversation should support:

- free participant-led turns;
- contextual follow-up;
- explicit clarification when references are ambiguous;
- recognition of corrections and uncertainty without claiming factual verification;
- a visible way to stop, redirect, or decline a line of questioning;
- preservation of the exact transcript.

### Uruguayan Spanish interaction requirements

The prototype should target adult native speakers in Uruguay rather than an abstract "Spanish" user.

The interaction policy and tests should therefore favour:

- natural Rioplatense syntax and pragmatics;
- voseo used naturally rather than mechanically;
- concise conversational turns rather than institutional or survey-like prose;
- sensitivity to how Uruguayans ordinarily narrate people, places, family relations, dates, rumours, political events, and remembered episodes;
- appropriate use of silence, acknowledgement, clarification, and topic return;
- no exaggerated regionalisms, performative slang, or attempts to imitate an accent in writing;
- no unnecessary explanation of Uruguayan institutions, places, political history, or ordinary cultural references unless the participant asks or ambiguity requires it;
- preservation of the participant's own vocabulary rather than normalising it into another Spanish variety;
- avoidance of therapy-like, police-interview, journalistic-interview, customer-service, and survey registers.

Naturalness is an interaction requirement, not merely a localisation setting.

### Conversation workbench

A second pane or mode that operates on the captured conversation.

Initial functions:

- select one or more turns;
- select a passage within a turn where practical;
- annotate selected text;
- attach status labels such as uncertain, hearsay, correction, withdrawn, significant;
- extract provisional entities/events/themes with exact turn references;
- connect a correction to the earlier material it modifies;
- inspect raw transcript beside derived material;
- edit or delete provisional derived material without changing the source transcript;
- export the session as JSON and readable Markdown.

Automatic extraction may use the same LLM as the conversation for prototype speed, but generated structures must remain visibly provisional and editable.

## Deliberate non-goals

The prototype does not need:

- production database architecture;
- authentication;
- cloud deployment;
- final archival schema;
- long-term preservation guarantees;
- final consent workflow;
- final security design;
- final model/provider choice;
- backward compatibility;
- migration path to the production system;
- real participant data.

## Suggested technical shortcut

For the disposable prototype, prefer a deliberately small stack:

- one local web app;
- simple server-side model calls;
- session state in memory or local JSON;
- minimal dependencies;
- provider configuration through environment variables;
- no framework decisions justified by hypothetical future scale.

The implementation may be replaced completely after testing.

## Success criteria

The first prototype is successful when:

1. a user can conduct a multi-turn conversation without the interaction obviously collapsing into a scripted questionnaire;
2. the conversation reads as plausible, natural Uruguayan Spanish to a native speaker rather than generic international Spanish or translated chatbot prose;
3. the system can make contextually relevant follow-ups while avoiding unsupported factual assertions;
4. the full conversation is preserved exactly;
5. the user can inspect and manually work on individual turns and passages;
6. provisional extraction remains linked to exact source turns;
7. corrections and uncertainty can be represented without overwriting the earlier record;
8. a complete session can be exported and inspected independently of the application;
9. automated tests cover deterministic state, editing, traceability, and export behaviour;
10. manual scenario testing documents conversational failures as requirements for the eventual architecture.

## Testing approach

Use synthetic or researcher-authored scenarios. Do not use real participant testimony in this prototype phase.

Scenarios should deliberately include:

- uncertain dates;
- aliases and pronouns;
- contradictory recollections;
- corrections several turns later;
- refusal to answer;
- topic shifts;
- hearsay;
- colloquial Uruguayan phrasing;
- voseo and shifts between informal and more formal registers;
- references to local places or institutions that should not trigger unnecessary explanation;
- emotionally neutral but structurally realistic memory narratives;
- incomplete events and unresolved relationships.

Manual conversational review should explicitly score or note:

- naturalness for a Uruguayan native speaker;
- whether the next turn follows from the participant's previous turn;
- leading or presuppositional questions;
- repetitive questioning;
- unnecessary summaries;
- inappropriate certainty;
- generic chatbot language;
- foreign or unnatural Spanish usage;
- loss of participant vocabulary;
- handling of correction, uncertainty, refusal, and digression.

Evaluate interaction quality manually before adding formal metrics. The purpose of this phase is discovery rather than validation.
