# Collective-memory capture

This document records the conversational and representational consequences of building a system whose purpose is to capture dispersed collective memories of the disappeared. It should be read with [`DESIGN-FOUNDATIONS.md`](DESIGN-FOUNDATIONS.md).

The central insight from the current prototype and the research review is not that small stories, neighbours, contradictions or digressions have been neglected by oral history. They have not. The important computational condition is this:

> The historical significance of a recollection may not be observable at the moment when the conversational system has to decide what to do with it.

The research basis is developed in [*Collective-memory capture review — Conditions of Recollection*](https://github.com/krahd/academic-writing/blob/main/my_papers_2026/2026%20-%20NeurIPS%20RTCA%20-%20Collective%20Memories/COLLECTIVE-MEMORY-CAPTURE-REVIEW.md). The review compares Latin American memory institutions and memorial projects, truth-commission methods, community archives, crowdsourced contribution systems, computational oral-history systems and current AI information-elicitation research.

## Deferred collective significance

A participant might mention a nickname, a house, a relative's phrase, an uncertain year, an everyday routine or an apparently peripheral object. In one conversation there may be no basis for judging that fragment historically important. Another contribution may later reach the same person, place, phrase or association and change the significance of the earlier fragment.

The real-time interviewer therefore acts before corpus-level relations exist.

This does not mean that significance is hidden as a fixed fact inside the participant. Recollection is produced in a present interaction and is selective, situated and mediated. The system is not extracting a latent database from a person's memory.

It also does not mean that every utterance must be pursued. Conversation is finite, people tire, and questions have costs. The distinction is:

```text
not pursued conversationally
        ≠
discarded archivally
        ≠
historically insignificant
```

The system may decide not to pursue a fragment now. It should not silently infer from that decision that the fragment is irrelevant to the future corpus.

## Two kinds of relevance

### Conversational relevance

This is information the interviewer can legitimately use to decide the next interactional move:

- whether the participant is still speaking or appears to retain the floor;
- whether they introduced a path they appear to want to continue;
- whether they set a boundary;
- whether a reference is ambiguous enough to block understanding;
- whether a follow-up would be leading or presumptive;
- whether a previous system turn needs repair;
- whether an invitation to continue is preferable to another question.

### Historical or collective significance

This can emerge later through:

- recurrence across contributions;
- contradiction;
- shared people, nicknames, places or periods;
- kinship and social relations;
- documentary or archival evidence;
- later researcher interpretation;
- patterns that were unavailable to the participant and interviewer at capture time.

The first category belongs in the live interviewer. The second should not become a hidden real-time reward function.

## Consequence for interviewer policy

The interviewer should not optimise for immediate information gain or for the apparent historical importance of the current utterance.

A better objective is to avoid prematurely foreclosing participant-led paths whose significance cannot yet be evaluated.

That favours the following behaviour:

- tolerate digression instead of treating it automatically as task loss;
- allow uncertainty, hearsay and contradiction to remain as given;
- ask few questions and ground them in material the participant introduced;
- avoid demanding immediate explanation of every name, date or relation;
- follow participant momentum rather than a database-completion agenda;
- allow a brief acknowledgement, invitation to continue or no spoken intervention when a question would only occupy the floor;
- accept that a useful capture can contain unresolved fragments.

Current AI-interviewer work already demonstrates adaptive follow-up and emergent-theme discovery. The distinction here is not fixed versus adaptive interviewing. [YIELD](https://aclanthology.org/2026.acl-long.678/) formalises elicitation around institutional or task objectives; [Panfilova et al.](https://www.nature.com/articles/s41598-026-46517-7) evaluate adaptive follow-up quality. The present project adds the constraint that collective relevance may not be evaluable inside the current interview at all.

## Waiting is an interactional action

A mature speech system needs a legitimate action that produces no audible response. Call it `WAIT`, `YIELD`, or another implementation name; the semantics are what matter:

> remain ready, keep listening, do not claim the floor yet.

This is different from saying `Ajá.`. Every backchannel is an intervention. Sometimes it is useful; sometimes silence is the less intrusive response.

The current 1.7-second silence detector is a prototype endpointing heuristic, not a definition of when a recollection has ended. [OHA evaluation guidance](https://oralhistory.org/oha-guidelines-for-the-evaluation-of-oral-historians/) explicitly recognises the importance of silence, and [Kubo et al.](https://aclanthology.org/2026.sigdial-1.2/) show why observed turn shifts should not be treated as uniquely correct binary ground truth under turn-taking ambiguity.

For the future full-duplex system, turn management should distinguish technical readiness from the decision to claim the conversational floor.

## Ground rules visible to the participant

Two mechanisms from evidence-based interviewing are strong enough to test, while not being imported wholesale from forensic protocols:

- explicitly make `I don't know / I don't remember` an acceptable response;
- explicitly invite the participant to correct the system when it misunderstands them.

These permissions should be known by the participant, not only hidden in a system prompt. Their wording must be tested for naturalness and appropriateness in Uruguay.

The system should also make clear, progressively and without a long procedural preamble, that:

- a contribution can be small;
- it does not need to be a complete story;
- second-hand material can be contributed as second-hand material;
- uncertainty is acceptable;
- the participant can skip a topic;
- the participant can pause or stop.

This is especially important for contributors who may otherwise believe that they “do not know enough” to have anything worth recording.

## Local refusal is not global withdrawal

`De eso no quiero hablar` is not equivalent to ending the session and is not necessarily a request to withdraw earlier material.

The production controller needs a participant-owned local boundary, conceptually something like `DECLINE_TOPIC`:

1. abandon that branch;
2. do not ask why;
3. do not return to it later unless the participant does;
4. record the boundary as interactional context;
5. do not interpret the refusal itself as evidence about the underlying historical event.

This is distinct from `PAUSE`, `STOP`, `WITHDRAW` and `REVOKE_DELETE`.

## Protocol and consent questions are in scope

Questions such as these are not off-topic commands:

- Who will hear this?
- What happens to the recording?
- Can I remove something later?
- Is this public?
- Are you recording now?

The production router should have a protocol/consent-information path backed by curated project information. An LLM must not invent the project's data policy, access rights or deletion guarantees.

## Capture first, interpret afterwards

A contribution should become safely preservable before extraction, entity linking or corpus analysis succeeds.

```text
participant contribution
        ↓
preserve source
        ↓
continue conversation
        ↓
provisional interpretation
        ↓
cross-session relations later
```

Failure to extract an entity must not make a recollection disappear. Poor ASR must not erase the audio. Lack of a current cross-session connection must not make a fragment non-recordable.

This ordering is already visible in the prototype's staged memory field and should survive as a production invariant even if the implementation changes completely.

## The live interviewer is archive-blind by default

The accumulated corpus must not automatically become context for later live interviews.

Otherwise the system creates a feedback loop:

```text
participant A contributes X
        ↓
archive represents X
        ↓
interviewer asks participant B about X
        ↓
participant B now contributes X-related material
        ↓
system reads the result as independent convergence
```

That is recursive contamination. The current session-local interviewer happens to avoid it; the production system should make this an explicit default boundary.

Archive-informed interviewing may be a legitimate future research condition, but only when deliberately designed, separately consented where necessary, and recorded as intervention. It must not be the silent default.

## Long conversations and retrieval

Context limits should not be solved by replacing older source with a generated summary and then treating that summary as memory.

For long or multi-session conversations, retrieval should prefer exact participant source passages:

```text
participant: "Volviendo a lo que te decía de Julio..."
        ↓
retrieve exact earlier participant passages about Julio
```

A generated summary may be useful as provisional interpretation, but if it enters interviewer context its provenance and status should be explicit. Otherwise consolidative interpretation becomes a cause of later source formation.

## Cross-session relations are hypotheses, not string matches

The current disposable memory field merges extracted nodes with the same conservatively normalised label. This is useful for making accumulation visible, but it is not a production identity model.

`Julio` in two conversations may refer to different people. `mi tío Aníbal` and `Aníbal` may refer to the same person, but the kinship phrase also carries relational information that simple normalisation discards.

A production model should distinguish at least:

```text
recollection A → mention A: "Julio"
recollection B → mention B: "Julio"

mention A ── candidate-coreference ── mention B
```

A shared historical entity should appear only through an explicit, provisional linkage with provenance and revision history.

Possible states include:

- same surface label;
- candidate same referent;
- researcher-supported identity;
- externally corroborated identity;
- rejected identity hypothesis.

The interface must not collapse these into one visual relation.

## Preserve social relationships, not only canonical names

A phrase such as `mi tío Aníbal` contains at least two pieces of potential derived material:

- a candidate person name, `Aníbal`;
- a narrator-to-person kinship relation, `tío`.

The source phrase remains primary. Name normalisation may assist retrieval, but production extraction should preserve relational descriptors rather than treating them as noise around entity resolution.

## Temporal interpretation remains provisional

The prototype chronology turns framed two-digit years such as `el 76` into 1976. In the target historical corpus that is often reasonable, but it remains an interpretation.

A mature temporal model should retain:

- exact source phrase;
- candidate normalisations;
- evidence used to choose among them;
- uncertainty and source attribution.

A phrase such as `en el 23` must not be silently forced into 1923 or 2023 without context.

## Recurrence is not truth

The memory field makes recurrent material visually prominent because recurrence is useful for seeing accumulation. Production views must state what that prominence means.

`mentioned in seven conversations` is defensible.

`important`, `credible`, `confirmed`, or `true` do not follow from mention count.

Graph size, colour, ranking, search order and other visual variables are therefore part of the representation policy, not neutral decoration.

## Do not expose the aggregate corpus to participants by default

Showing participant B that other people mentioned `Julio`, `1976` or a particular house can itself suggest candidate material before B articulates an independent recollection.

The eventual system should therefore separate:

### Participant capture interface

- conversation;
- clear microphone/recording state;
- pause, stop and rights controls;
- participant review/correction where appropriate;
- minimal protocol information.

### Researcher/corpus interface

- accumulated memory field;
- chronology;
- search;
- candidate cross-session relations;
- interpretation and provenance;
- governance/access controls.

The current prototype deliberately places conversation and memory field beside one another because it is a research/demo apparatus. That layout is not a production participant-interface specification.

## Capture can be multimodal

Conversation should be the primary interaction, not the only possible contribution type.

When someone says `Tengo una foto`, `Guardé una carta`, or refers to an object, the mobile system should eventually make it easy to attach:

- photographs;
- documents;
- letters and notes;
- audio/video;
- objects captured by camera;
- locations where appropriate;
- other participant-supplied media.

The attachment should remain linked to the conversational moment in which it was introduced and carry its own source, consent and provenance information.

## The archive is not collective memory

The project name should not lead the implementation into treating collective memory as a database assembled by summing individual records.

The archive stores contributions and the system exposes relations among acts of recollection. Collective remembering is social, communicative and mediated. The graph, chronology and future derived views are apparatuses for supporting or studying that process, not computational equivalents of the collective memory itself.

## Design test for deferred significance

The evaluation suite should include paired or multi-session scenarios in which an initially weak fragment becomes relationally meaningful only later.

Example:

1. Conversation A: `Había uno al que le decían Tito, que a veces aparecía por casa.`
2. Conversation B: `Tito vivía por La Teja.`
3. Conversation C: `Creo que Julio usaba el nombre Tito.`

At the time of A, the interviewer cannot know which later relation will appear. Evaluation should ask whether the real-time policy allowed A to survive in a useful form without either dismissing it or aggressively interrogating it.

Comparisons may include:

- aggressive information-seeking policy;
- conventional adaptive semi-structured policy;
- restrained policy designed for deferred collective significance.

The important outcome is not whether every fragment receives a follow-up. It is whether the capture policy avoids making immediate relevance judgements irreversible.
