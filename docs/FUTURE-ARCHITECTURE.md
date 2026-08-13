# Future system architecture

This document records the production direction discovered through the disposable prototype and the research reviews. It is deliberately more stable than the current code and deliberately less specific about technologies that have not yet been tested.

The production target is a mobile-first, speech-first system for capturing collective memories of the disappeared. The final interaction should be full duplex and natural enough that contributors do not have to learn the mechanics of a recording application in order to speak.

The current desktop, browser-based, continuous half-duplex prototype is an experimental instrument. It should not be incrementally hardened into production by default.

See also:

- [`DESIGN-FOUNDATIONS.md`](DESIGN-FOUNDATIONS.md)
- [`COLLECTIVE-MEMORY-CAPTURE.md`](COLLECTIVE-MEMORY-CAPTURE.md)
- [State of the Art Review](https://github.com/krahd/academic-writing/blob/main/my_papers_2026/2026%20-%20NeurIPS%20RTCA%20-%20Collective%20Memories/STATE-OF-THE-ART-REVIEW.md)
- [Collective-memory capture review](https://github.com/krahd/academic-writing/blob/main/my_papers_2026/2026%20-%20NeurIPS%20RTCA%20-%20Collective%20Memories/COLLECTIVE-MEMORY-CAPTURE-REVIEW.md)

## Production interaction target

The participant-facing experience should be substantially simpler than the present research interface.

A likely interaction is dominated by voice and a few explicit controls:

```text
┌─────────────────────────────┐
│                             │
│       recording state       │
│                             │
│      Estamos escuchando     │
│                             │
│             ●               │
│                             │
│       Pausar    Terminar    │
│                             │
└─────────────────────────────┘
```

The exact wording and visual treatment require design and participant research. The principle is that database, annotation and model mechanics belong behind the interaction rather than in front of the contributor.

The participant interface should not expose the aggregate memory graph by default. Corpus views belong to researcher/access interfaces because showing existing cross-session material can itself influence later recollection.

## Mobile-first does not yet imply one inference architecture

The project should not decide prematurely that all inference must run locally or remotely. Four broad deployment patterns remain plausible.

### Fully local

```text
phone
  ├── duplex audio
  ├── ASR
  ├── interviewer model
  ├── extraction
  └── TTS
```

Advantages include offline use and a strong privacy boundary. Costs include model quality, memory pressure, battery, thermals, device fragmentation and difficult support for older or inexpensive phones.

### Local speech, trusted remote inference

```text
phone: duplex audio / endpointing / perhaps ASR / encryption
                       ↓
trusted service: interviewer / interpretation
                       ↓
phone: TTS / playback
```

This can improve model quality and reduce device load, while creating network and server-side privacy requirements.

### Remote real-time speech

The phone acts mainly as a secure low-latency speech endpoint. This may provide the best conversational performance but creates the strongest dependency on connectivity and the largest remote exposure of sensitive material.

### Adaptive hybrid

Capabilities can be allocated according to device, connectivity and policy. For example, capture and encryption may always be local while conversational inference can switch between local and trusted infrastructure under explicit rules.

No option is currently selected. Future experiments should compare them using the actual requirements of this project:

- conversational latency and naturalness;
- full-duplex capability;
- privacy and threat model;
- model quality in Uruguayan Spanish;
- accessibility across realistic phones;
- offline/intermittent operation;
- battery and thermal cost;
- bandwidth and financial cost;
- reproducibility and model governance;
- long-term maintainability.

## Full duplex is a production requirement

[Full-Duplex-Bench-v2](https://aclanthology.org/2026.acl-short.4/) confirms that simultaneous listening/speaking, correction and entity continuity remain active technical problems. For this project, full duplex is required primarily because the interaction should feel like conversation, not because low latency is an end in itself.

A participant should be able to:

- interrupt immediately;
- correct the system before it finishes a mistaken question;
- restart or revise a sentence;
- continue after a pause that appeared to be a turn boundary;
- overlap naturally;
- change direction without waiting for a synthetic turn to finish.

The authority should be asymmetric:

- participant interruption of the system should be easy and immediate;
- system interruption of the participant should be conservative.

This asymmetry follows both from naturalness and from capture fidelity. A system that occupies the floor can prevent material or self-repair from being articulated.

## System latency and participant-owned time are different quantities

Technical latency should generally be reduced after a participant turn is actually available to the system.

Participant silence should not automatically be treated as technical latency to eliminate. [OHA evaluation guidance](https://oralhistory.org/oha-guidelines-for-the-evaluation-of-oral-historians/) recognises the role of silence, and [Kubo et al.](https://aclanthology.org/2026.sigdial-1.2/) demonstrate why turn shifts are not uniquely determined binary events.

Future full-duplex evaluation should therefore measure separately:

- time from usable end-of-turn evidence to model response;
- time to first audible system speech;
- participant pause duration;
- probability of participant continuation;
- system floor claims that cut off continuation;
- participant barge-in latency;
- cancellation latency after barge-in;
- overlapping speech;
- whether system speech caused or obstructed repair.

A system can be computationally fast and interactionally restrained.

## Capture, archive and access are separate architectural concerns

A useful production decomposition is:

```text
CAPTURE DEVICE
    │
    ├── source audio / text / media
    ├── participant controls and consent state
    ├── mediation events
    ├── local capture metadata
    └── secure pending contribution
             │
             ▼
        SECURE SYNC
             │
             ▼
SOURCE + MEDIATION STORE
             │
             ▼
INTERPRETATION LAYER
 entities / candidate links / chronology / themes
             │
             ▼
ACCESS + RESEARCH LAYERS
 search / maps / graph / review / publication
```

A contribution should remain safely preservable if the interpretation layer is unavailable. Corpus analytics should not be required to complete capture.

This separation also enables stronger access and privacy controls. The process that talks to the participant need not have the same privileges as the process that performs corpus-wide analysis.

## Source, mediation and interpretation

These are not the purpose of the project, but they are a useful production separation because each has different epistemic and governance status.

### Source

Participant-produced material.

For typed interaction, the submitted text is source.

For voice interaction, the original audio is the primary captured source. A transcript is a representation of that audio, not a replacement.

Attachments such as photographs, documents or additional recordings are their own source objects.

### Mediation

Anything the system presents or does that can shape subsequent contribution.

A production mediation record should be capable of retaining:

- exact model-generated candidate utterance;
- policy/router/guard decisions;
- exact text actually approved for rendering;
- exact audio actually played;
- playback start and stop;
- interruption/cancellation point;
- overlap with participant speech;
- source turns supplied to the model;
- model, prompt/policy version and inference configuration;
- system fallback or deterministic protocol response;
- relevant timing/paradata.

The distinction between generated and actually presented output matters. If the model generates fifteen words but the participant interrupts after four, only the audible portion directly mediated the next source turn.

### Interpretation

Machine- or researcher-derived structures such as:

- people, organisations, objects and places;
- dates and temporal candidates;
- themes;
- events;
- candidate identity/coreference links;
- kinship and social relations;
- summaries;
- cross-session hypotheses.

Interpretation objects should carry exact source references, origin, model/configuration where applicable, revision history and status.

Model confidence is model metadata. It must not be rendered as narrator certainty.

## Voice source hierarchy

For spoken contributions the data model should distinguish:

```text
participant audio                    source
       ↓
ASR transcript                       machine derivation
       ↓
participant-corrected transcript     participant-authorised derivation
       ↓
research/editorial transcript        research derivation
```

Later forms must not silently overwrite earlier ones.

Names and places deserve special scrutiny because a single ASR error can propagate into entity extraction and cross-session linking.

## Participant-owned correction and repair

At least three repair relations are needed:

```text
participant source ─corrects→ participant source
participant source ─corrects→ machine mediation
research revision   ─corrects→ derived interpretation
```

Example:

`No, yo no dije que fuera mi hermano.`

This is not merely a corrected participant fact. It can be a correction of an interviewer presupposition. The mistaken machine turn must remain visible as mediation because it may have caused the participant's next utterance.

## Consent as versioned, scoped state

Production consent should not be one Boolean value.

Potential scopes include:

- preserving audio;
- preserving transcript;
- machine transcription;
- machine-derived interpretation;
- linking across contributions;
- researcher access;
- public access;
- publication of excerpts;
- use of images/documents;
- model training or evaluation;
- retention period;
- withdrawal and revocation behaviour.

Every captured/derived object should be able to identify the consent state governing its creation and use.

The [OHA Core Principles](https://oralhistory.org/oha-core-principles/) and [OHA ethics guidance](https://oralhistory.org/oha-statement-on-ethics/) are useful baselines for ongoing consent, transparency, refusal, review, privacy and protection from harm, but the project's final governance must be developed for its own Uruguayan institutional and political context.

## Relational privacy

A contributor can reveal sensitive material about another person who never used the system. Privacy modelling must therefore include people mentioned in contributions and relations among people, not only authenticated users.

Questions for the production design include:

- when may a living person's name be exposed to researchers or the public;
- whether cross-session identity linking should require additional review;
- how restricted material affects derived views;
- how search results avoid revealing that a person appears in protected testimony;
- how revocation interacts with relations created from multiple sources;
- how aggregate statistics can leak rare identities or events.

## Threat model

Before participant deployment the project needs a written threat model covering at least:

### Malicious conversational input

- prompt injection;
- attempts to reveal policies/prompts;
- attempts to turn the system into a general assistant;
- attempts to extract another participant's material.

### Corpus integrity

- deliberate false contributions;
- coordinated narratives and poisoning;
- automated/bot submissions;
- impersonation;
- repeated spam;
- manipulated documents or media.

The system must preserve the distinction between `a contribution was made` and `the contribution is historically verified`.

### Device and transport

- stolen or compromised phones;
- local caches;
- microphone permissions;
- network interception;
- server compromise;
- backup and log leakage;
- model-provider retention.

### Derived-data leakage

- vector stores;
- embeddings;
- entity indexes;
- logs;
- model prompts;
- aggregate graphs;
- search suggestions.

Deleting or restricting source while leaving derived leakage intact is not meaningful revocation.

## Distributed and intermittent capture

Mobile deployment should assume imperfect connectivity. Capture should not require a round trip to the global archive before a participant contribution can be durably staged.

A production contribution package may need:

- local encrypted source storage;
- append-only capture/mediation log;
- consent state;
- locally assigned stable identifiers;
- resumable secure sync;
- idempotent upload;
- server acknowledgement;
- explicit cleanup policy after successful sync.

If remote inference is required, the system should still define what happens during network loss and which material is temporarily stored locally.

## Accessibility and older participants

[W3C WAI guidance](https://www.w3.org/WAI/older-users/) notes that older users may experience changes in vision, hearing, dexterity, concentration or short-term memory and that established accessibility standards address much of this variation.

Production implications include:

- large, clear controls;
- high contrast and scalable text;
- minimal navigation depth;
- consistent placement and terminology;
- visible recording state;
- no reliance on fine gestures;
- no dependence on reading long instructions while speaking;
- adjustable audio output;
- captions/transcript availability without making reading mandatory;
- tolerance for slower interaction and repeated explanations;
- recovery from accidental taps or app switching;
- direct testing with older participants rather than designing from age stereotypes.

Speech-first design reduces some burdens and creates others. Hearing, speech variation, ASR quality and privacy of spoken interaction must all be tested.

## Multimodal contributions

The mobile interface should eventually allow the conversation to open a low-friction path to other source material.

If a participant mentions a photograph, letter, document or object, they should be able to attach it without leaving the conceptual context of the conversation. The system should preserve:

- original captured file;
- capture timestamp and device metadata where appropriate;
- participant description;
- exact conversational source turn that introduced it;
- rights/consent information;
- later interpretation separately.

No computer-vision description should replace the participant's own description.

## Archive blindness and privilege separation

The live interviewer is archive-blind by default. This is both an epistemic and security boundary.

The capture process should have the minimum corpus-wide access necessary to function. Researcher and access applications can have different capabilities under explicit authorisation.

Do not solve conversational context by giving the interviewer general semantic search over the collective archive.

## Production questions intentionally unresolved

The following are open research/design decisions, not omissions to fill with defaults:

- local versus remote model placement;
- iOS/Android/native/web implementation strategy;
- exact full-duplex speech stack;
- authentication model;
- institutional host/steward;
- encryption/key management;
- identity and pseudonym strategy;
- exact participant review workflow;
- consent and revocation rules;
- public-access model;
- entity-resolution governance;
- moderation and malicious-contribution policy;
- relationship to official investigative or human-rights institutions.

Each should be decided with evidence and project governance rather than inherited from the disposable prototype.
