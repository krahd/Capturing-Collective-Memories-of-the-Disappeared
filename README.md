# Capturing Collective Memories of the Disappeared

This repository contains the new implementation of the research project *Capturing Collective Memories of the Disappeared with Artificial Intelligence*.

The project is distinct from `desaparecidos.uy`, which is a separate computational memorial artwork.

## Current phase: disposable interaction prototype

The immediate goal is to build a first working prototype that demonstrates two things:

1. a conversational interaction that feels natural enough to support memory elicitation;
2. an apparatus for working on the conversation itself after and during capture.

This prototype is intentionally disposable. Its code does not need to survive into the final research system and should not constrain the later architecture.

The prototype exists to expose interaction requirements, failure modes, useful conversational operations, and research questions. Once it works and has been tested, the project will design the proper architecture and implement the actual system from first principles.

## Prototype priorities

### Natural conversational interaction

The prototype should support a fluid, participant-led conversation rather than a questionnaire disguised as chat. It should be able to:

- sustain context across turns;
- ask relevant, non-leading follow-up questions;
- recognise uncertainty, hesitation, correction, digression, and partial recollection;
- avoid treating remembered material as established fact;
- allow the participant to redirect the conversation;
- make conversational repair possible;
- preserve the participant's wording rather than silently normalising it into an authoritative narrative.

Voice interaction may be added if it materially improves the prototype, but the first objective is interaction quality rather than infrastructure completeness.

### Apparatus for working on the conversation

The prototype should expose the conversation as material that can be inspected and worked on rather than only stored as a transcript. Candidate operations include:

- turn-by-turn transcript inspection;
- marking passages as uncertain, hearsay, corrected, withdrawn, or especially significant;
- linking later corrections to earlier turns;
- extracting provisional people, places, dates, events, relationships, and themes while preserving links to source turns;
- comparing contradictory or alternative recollections without resolving them automatically;
- participant review and correction of extracted material;
- annotations and researcher notes kept distinct from participant speech;
- export of both raw conversation and derived structures with provenance intact.

These are prototype hypotheses, not final architectural commitments.

## Development rule

Optimise this phase for speed of learning, observability, and interaction quality. Avoid premature production architecture, migration guarantees, long-term storage design, or abstraction intended only for future reuse.

The eventual production system will be designed after the prototype has been exercised and its requirements are better understood.

## Research boundary

The system is intended to support the elicitation and preservation of situated collective memories concerning Uruguay's disappeared. It is not an adjudication system and should not convert recollection, hearsay, uncertainty, contradiction, or silence into a single authoritative historical account.

Initial development and testing should use synthetic, researcher-authored, or already-public material until appropriate governance and human-subjects procedures are in place for participant deployment.
