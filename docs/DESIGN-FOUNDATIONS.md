# Design foundations

This document records the long-lived design direction for *Capturing Collective Memories of the Disappeared with Artificial Intelligence*. It is not a specification of the disposable prototype. `GOAL.md` and `PROTOTYPE.md` describe what the current prototype is meant to test; this document records what those tests are in service of.

The central design problem is simple to state and difficult to satisfy:

> Capture collective memories of Uruguay's detained-disappeared.

Everything else in the system follows from that objective. Provenance, conversational restraint, privacy, accessibility, representation, security and deployment architecture are requirements because the material is dispersed, sensitive, relational, politically and historically complex, and often held by people for whom a conventional archival or technical interface would be an unnecessary barrier.

## Research record

Two research reviews in `krahd/academic-writing` are direct inputs to these design foundations:

- [State of the Art Review — *The Conversation Is Not the Record*](https://github.com/krahd/academic-writing/blob/main/my_papers_2026/2026%20-%20NeurIPS%20RTCA%20-%20Collective%20Memories/STATE-OF-THE-ART-REVIEW.md)
- [Collective-memory capture review — *Conditions of Recollection*](https://github.com/krahd/academic-writing/blob/main/my_papers_2026/2026%20-%20NeurIPS%20RTCA%20-%20Collective%20Memories/COLLECTIVE-MEMORY-CAPTURE-REVIEW.md)

The reviews are literature maps, novelty audits and source ledgers. They should be consulted before changing the interviewing policy, representation model, evaluation framework or the boundary between capture and the accumulated corpus.

Selected external anchors were re-checked on 13 August 2026 against primary or authoritative sources:

- [Oral History Association Core Principles](https://oralhistory.org/oha-core-principles/) treats oral history as both interview process and resulting record, and emphasises the dynamic relationship between interviewer and narrator, ongoing consent, community context and protection from harm.
- [OHA Best Practices](https://oralhistory.org/best-practices/) and [OHA Evaluation Guidelines](https://oralhistory.org/oha-guidelines-for-the-evaluation-of-oral-historians/) support open-ended questioning, careful listening, follow-up without leading, flexibility and recognition of silence.
- [OHA Statement on Ethics](https://oralhistory.org/oha-statement-on-ethics/) makes privacy, safety, informed consent, refusal, review and subsequent use part of the complete process rather than concerns added after recording.
- [Memoria Abierta, *Testimonio y Archivo*](https://memoriaabierta.org.ar/wp/testimonio-y-archivo-metodologia-de-memoria-abierta/) provides a directly relevant Latin American methodological precedent for relational, contextual oral testimony and long-term preservation.
- [YIELD, ACL 2026](https://aclanthology.org/2026.acl-long.678/) formalises information-elicitation agents around institutional or task-oriented objectives. It is a useful contrast because the eventual significance of a recollection in this project may not be representable as immediate task progress.
- [Panfilova et al., *The AI interviewer*, Scientific Reports 2026](https://www.nature.com/articles/s41598-026-46517-7) shows that adaptive LLM interviewing can be evaluated for necessity, context-awareness, openness, benevolence and justified skipping, while also showing substantial model-dependent trade-offs.
- [Pataranutaporn et al., IUI 2025](https://doi.org/10.1145/3708359.3712112) demonstrates increased false recollection under deliberately misleading chatbot interaction. [Dando and Adam, Scientific Reports 2025](https://www.nature.com/articles/s41598-025-93281-1) supplies the necessary counterexample: a carefully protocolised chatbot initial-account procedure improved later recall without increasing errors. The design implication is policy sensitivity, not a blanket claim that conversational systems necessarily contaminate memory.
- [Full-Duplex-Bench-v2, ACL 2026](https://aclanthology.org/2026.acl-short.4/) evaluates correction, entity tracking, safety and turn-taking in full-duplex systems and reports continuing difficulty with overlap and correction.
- [Kubo et al., SIGDIAL 2026](https://aclanthology.org/2026.sigdial-1.2/) argues that turn-taking observations should not be treated as uniquely correct binary ground truth under inherent interactional ambiguity.
- [Heindl, Kolb and Gloe, AAAI 2024](https://ojs.aaai.org/index.php/AAAI-SS/article/view/31822) provides a contemporary precedent for interactive digital testimony that explicitly excludes generated witness responses or actions.
- [W3C WAI guidance for older users](https://www.w3.org/WAI/older-users/) documents overlapping visual, hearing, dexterity and cognitive accessibility needs and points to established accessibility standards rather than a separate category of “senior-friendly” interface design.

These sources support requirements and cautions. They do not validate this system, its conversational policy or its cultural adequacy in Uruguay. Those require empirical work with the people and institutions involved.

## Objective hierarchy

### 1. Capture collective memories

The system should make it possible for many people to contribute memories, fragments, inherited accounts, relationships, uncertainty, corrections, objects and contextual traces connected to the disappeared.

A contributor should not need to arrive with a polished testimony, a recognised institutional role, or a prior judgement that what they remember is historically important. A small recollection, nickname, family phrase, place, image, object or second-hand account can be a legitimate starting point.

### 2. Make contribution accessible enough to happen

Capture fails if the interface itself prevents contribution. The eventual participant-facing system should therefore minimise technical and procedural burden.

The intended production direction is mobile-first and speech-first. Older participants are a central design population, not an edge case. Design must account for variable eyesight, hearing, dexterity, concentration, memory, technical familiarity and network quality without assuming that age determines any particular ability.

Conversation is not merely a convenient input method. It can help a person formulate an under-developed recollection without requiring them to translate it first into a database field or an archival category.

### 3. Preserve fidelity without pretending recollection is a factual database

Participant-produced material must remain distinguishable from machine intervention and later interpretation. Uncertainty, hearsay, contradiction, correction, reticence and incompleteness are not defects to be silently repaired.

For voice capture, original participant audio is the primary captured source. ASR text is a machine-derived representation of that source. A participant-corrected transcript is another layer and must not silently overwrite either the audio or the original ASR output.

### 4. Protect people and relationships

The corpus can contain sensitive information about contributors and about other living people who did not choose to participate. Privacy is therefore relational as well as individual. Access, publication, cross-linking, model use, retention and withdrawal cannot be reduced to one consent checkbox.

The production system needs a threat model covering accidental disclosure, compromised devices, hostile or curious users, automated agents, poisoning, impersonation, prompt injection, extraction attacks and attempts to learn material from other contributors.

### 5. Represent complexity without premature resolution

The accumulated system must support partial, conflicting and uncertain material without forcing one canonical historical account. Cross-session relations are interpretations or hypotheses unless independently established; recurrence is not truth; visual prominence is not credibility.

The `campo de memoria` is an apparatus for exposing relations among acts of recollection. It is not itself “the collective memory”.

### 6. Make the accumulated material useful

The corpus should eventually support search, chronology, mapping, thematic exploration, relational analysis, research, memorialisation and other cultural or historical uses. Those products must remain traceable to their sources and must not silently become the source.

### 7. Provide durable governance

The production system needs explicit decisions about stewardship, ownership, consent, access levels, publication, correction, withdrawal, deletion, model use, security, retention and institutional responsibility. These cannot be delegated to an LLM.

## Problem families

The project should be evaluated against the following interacting problem families rather than against “chatbot quality” alone.

### Capture

- natural sustained conversation rather than questionnaire behaviour;
- eliciting without leading;
- fragments and under-formulated recollections;
- long, non-linear accounts;
- inherited and second-hand memory;
- uncertainty, contradiction and correction;
- silence, hesitation, association and topic changes;
- multiple sessions over time;
- attachment of photographs, documents, objects and other media to the point in the conversation where they arise.

### Accessibility

- older participants and age-related access needs;
- low technical literacy without patronising interface design;
- low visual and motor burden;
- hearing and speech variability;
- readable, understandable consent and control mechanisms;
- unreliable or expensive connectivity;
- assisted capture where appropriate without confusing who supplied which material.

### Fidelity

- ASR errors, especially names, places and local terms;
- interviewer suggestion and affirmation;
- model-generated consolidation of ambiguous material;
- correction without erasure;
- provenance of machine and researcher intervention;
- preservation of the exact material actually heard or seen by the participant.

### Privacy and safety

- sensitive political and personal information;
- living third parties;
- relational privacy;
- differentiated access;
- accidental disclosure;
- local-device compromise;
- remote-provider exposure;
- withdrawal and revocation;
- future reuse beyond the capture purpose.

### Adversarial conditions

- prompt injection and attempts to turn the interviewer into a general assistant;
- reported speech that resembles an application command;
- malicious or coordinated false contributions;
- automated agents submitting material;
- spam and corpus poisoning;
- impersonation;
- attempts to retrieve or infer other participants' contributions;
- poisoned documents or media introduced as attachments.

### Representation

- ambiguous people, nicknames and aliases;
- same-name/different-person and different-name/same-person cases;
- kinship and social relationships;
- uncertain or relative dates;
- hearsay chains and attribution;
- contradictory accounts;
- relations that become visible only across contributions;
- model and researcher interpretations that can change over time.

### Infrastructure and deployment

- mobile-first operation;
- full-duplex speech;
- offline or intermittently connected capture;
- local versus remote inference;
- battery, thermals and device coverage;
- secure synchronisation;
- model updates and reproducibility;
- long-term archival preservation distinct from the capture application.

## Long-lived design invariants

The following are current design commitments unless later evidence gives a strong reason to revise them.

1. The project objective is collective-memory capture, not the production of a technically sophisticated interviewer.
2. Preserve participant contribution before requiring successful interpretation.
3. Generated participant/testimony speech is prohibited in the source layer.
4. Participant source, machine mediation and derived interpretation remain distinguishable and traceable.
5. For speech, source audio and ASR transcript are different objects.
6. Correction, qualification and withdrawal should not silently rewrite earlier source material.
7. The live interviewer is session-local and archive-blind by default. Cross-participant corpus material must not automatically feed later interviewing.
8. Not pursued conversationally does not mean discarded archivally or historically insignificant.
9. Historical significance can emerge later, across contributions. Real-time policy must therefore avoid aggressive relevance filtering based only on the current conversation.
10. The participant must be able to stop, pause, decline a topic, correct the system and ask protocol/consent questions without model improvisation over their rights.
11. The final participant interface is mobile-first, speech-first and deliberately simpler than the current desktop research interface.
12. The production speech interface is intended to be full duplex. Participant interruption should be easy; system interruption should be conservative.
13. The aggregate memory field, chronology and other corpus views are researcher/access apparatuses, not default material shown to participants during capture.
14. Recurrence, graph centrality, model confidence and visual prominence must not be presented as historical truth or credibility.
15. Identity resolution and cross-session linking are provisional interpretive operations, not string-matching facts.
16. Capture and archive/access should be architecturally separable. A contribution must be safely preservable before corpus-wide processing succeeds.
17. Privacy, consent, access and threat modelling are production architecture, not post-processing features.
18. No claim of usability, safety, naturalness, cultural validity or successful memory capture is justified before the corresponding empirical evidence exists.

## Terminology

`source` refers to participant-produced material as captured. In typed interaction this is the submitted text; in voice interaction the primary captured source is audio.

`mediation` refers to system/interviewer intervention that can affect how a recollection is articulated. This includes what was actually presented to the participant, not only what a model generated internally.

`interpretation` refers to machine- or human-derived structures such as entities, candidate relations, labels, summaries, temporal normalisation or identity hypotheses.

`recollection` is preferred over `fact` for a participant contribution represented in the memory field.

`collective memory` names the social and communicative phenomenon the project is trying to support and study. The database, graph or archive is not identical to that phenomenon.

## Relation to the disposable prototype

The current desktop prototype intentionally violates or postpones some production requirements. It is half duplex, uses local JSON persistence, has no final consent/governance workflow, uses simplified entity matching and exposes a researcher-oriented memory field next to the conversation. These are acceptable only because the current phase uses researcher-authored/synthetic material and exists to discover requirements.

Do not harden those shortcuts into the production architecture by default. When a prototype shortcut conflicts with this document, treat the conflict as a recorded design debt to be resolved by the next architecture rather than as evidence that the shortcut became a project principle.
