# Disposable prototype plan

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

### Conversation workbench

A second pane or mode that operates on the captured conversation.

Initial functions:

- select one or more turns;
- annotate selected text;
- attach status labels such as uncertain, hearsay, correction, withdrawn, significant;
- extract provisional entities/events/themes with exact turn references;
- connect a correction to the earlier material it modifies;
- inspect raw transcript beside derived material;
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
2. the system can make contextually relevant follow-ups while avoiding unsupported factual assertions;
3. the full conversation is preserved exactly;
4. the user can inspect and manually work on individual turns;
5. provisional extraction remains linked to exact source turns;
6. corrections and uncertainty can be represented without overwriting the earlier record;
7. a complete session can be exported and inspected independently of the application;
8. a short test session reveals concrete requirements for the eventual architecture.

## Testing approach

Use synthetic or researcher-authored scenarios that deliberately include:

- uncertain dates;
- aliases and pronouns;
- contradictory recollections;
- corrections several turns later;
- refusal to answer;
- topic shifts;
- hearsay;
- emotionally neutral but structurally realistic memory narratives;
- incomplete events and unresolved relationships.

Evaluate interaction quality manually before adding formal metrics. The purpose of this phase is discovery rather than validation.
