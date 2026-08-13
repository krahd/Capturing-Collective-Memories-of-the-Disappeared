# Status

**Date:** 13 August 2026  
**Phase:** disposable interaction prototype plus production-design synthesis  
**Current implementation baseline:** speed-improved local prototype (`9017bb1`, followed by documentation-only commits)  
**Mechanical verification:** GitHub Actions was green on the implementation baseline; verify again after the documentation sync  
**Live-model Uruguayan-Spanish evaluation:** informal single- and multi-turn checks have been run; the revised policy still needs a fresh sustained human review  
**Voice:** continuous local half duplex implemented; real 10–15-turn spoken verification still pending  
**Participant data:** none; current evaluation uses researcher-authored/synthetic material

## Project objective

The central design problem is to capture collective memories of Uruguay's detained-disappeared. The conversational agent, provenance model, memory field and technical architecture are means to that end.

The project now has a clearer distinction between:

- the current disposable prototype, used to discover interaction and representation requirements;
- long-lived design guidance for the eventual mobile production system.

The documentation map is [`docs/README.md`](docs/README.md). Long-lived guidance is in:

- [`docs/DESIGN-FOUNDATIONS.md`](docs/DESIGN-FOUNDATIONS.md);
- [`docs/COLLECTIVE-MEMORY-CAPTURE.md`](docs/COLLECTIVE-MEMORY-CAPTURE.md);
- [`docs/FUTURE-ARCHITECTURE.md`](docs/FUTURE-ARCHITECTURE.md);
- [`docs/EVALUATION-FRAMEWORK.md`](docs/EVALUATION-FRAMEWORK.md).

These documents explicitly link the two research reviews in `krahd/academic-writing` that motivated the current design synthesis.

## Current implementation

Implemented in the disposable prototype:

- two coordinated research/demo views: Conversation and Campo de memoria;
- provider-neutral model boundary plus Ollama-native optimisation when applicable;
- a separate small `LLM_ROUTER_MODEL` can classify turns without paying a 30B call before every interview response;
- extraction defaults to the small router model when configured, can be overridden separately, is queued, waits for conversational quiet and can be pre-empted by a new conversational call;
- configured local models are warmed and HTTP connections are reused;
- interview working context is bounded instead of growing indefinitely;
- participant-led conversational policy for natural adult Uruguayan/Rioplatense Spanish;
- structural scope control separating testimony, uncertainty, correction, participant controls and off-topic commands;
- five current interviewer moves: `BACKCHANNEL`, `INVITE_CONTINUE`, `FOLLOW_UP`, `CLARIFY`, `ACKNOWLEDGE`;
- zero-question replies are permitted; questions are not required on every turn;
- guard checks for grounding, repetition and unsupported certainty over hedged/hearsay material;
- reported speech is protected from being mistaken for participant STOP/DELETE instructions;
- exact turn-by-turn text preservation;
- append-only session record attributing participant, researcher, model and system actions;
- model/researcher-derived interpretations with exact source-turn provenance, revision history and withdrawal/deletion distinction;
- JSON and Markdown export;
- automatic background extraction;
- memory field with recollections as first-class nodes and deliberately weak `menciona` relations;
- chronology view retaining contradictory dates rather than adjudicating them;
- cached aggregate field/chronology and server-sent field-change events instead of timed polling bursts;
- seven-conversation researcher-authored demo corpus and recorded example session;
- continuous local half-duplex voice using browser audio, ffmpeg, resident whisper.cpp where configured, and Piper;
- microphone stream/analyser retained across turns;
- current prototype endpointing at 1.7 seconds of detected silence;
- latency instrumentation for endpointing/ASR and conversational model stages;
- deterministic automated tests and researcher-authored interaction/evaluation tooling.

## Current prototype semantics and their limits

The memory field demonstrates accumulation but does not solve production knowledge representation.

- Recollections are first-class nodes so extracted material does not replace participant wording.
- Recollection-to-derived edges claim mention, not historical occurrence.
- A node is a person only when extraction explicitly classified it as `person`.
- Uncertainty, hearsay and correction remain properties/marks of the recollection rather than facts in the world.
- Contradictory dates coexist.
- The current prototype merges extracted nodes that share a conservatively normalised label. This is a visual heuristic for possible convergence, not historical identity resolution. Same label does not imply same referent.
- Kinship-prefix stripping currently helps the demo converge labels such as `mi tío Aníbal` and `Aníbal`, but production representation must preserve the relational information rather than treating it as noise.
- Two-digit years such as `el 76` are normalised for the prototype chronology. Production temporal interpretation must retain the exact phrase and represent normalisation as provisional.
- Graph prominence means recurrence/reach in stored conversations, not importance, credibility or truth.
- The `campo de memoria` is an apparatus for exposing relations among recollections; it is not claimed to be collective memory itself.

## Research/design synthesis completed 13 August 2026

Two current literature reviews materially sharpened the production direction:

1. AI/oral-history, memory-science and RTCA research supports treating conversational intervention as potentially consequential to the source, while avoiding the false claim that conversational AI is uniformly contaminating.
2. Comparative collective-memory capture research exposes a different real-time problem: historical significance can be deferred. A fragment that looks peripheral in one conversation can become significant only after later contributions create a cross-session relation.

Consequences now recorded as long-lived design commitments:

- preserve participant contribution before requiring successful interpretation;
- distinguish participant source, machine mediation and derived interpretation;
- for voice, original audio is source and ASR text is a machine-derived layer;
- generated testimony is prohibited in the participant source layer;
- correction/qualification/withdrawal do not silently rewrite earlier source;
- the live interviewer is session-local and archive-blind by default;
- cross-participant archive material must not automatically feed later interviews, because that can manufacture apparent convergence;
- `not pursued now` does not mean `discarded` or `historically insignificant`;
- real-time policy should avoid aggressive relevance filtering based only on one conversation;
- a future no-speech `WAIT/YIELD` action should be tested so computational readiness does not force a floor claim;
- participant rights/protocol questions need curated application-owned answers rather than model improvisation;
- local topic refusal needs to be distinguished from global STOP/WITHDRAW;
- cross-session identity/coreference should be mention-based and provisional rather than silent string merging;
- participant and researcher/corpus interfaces should be separated in production;
- the aggregate corpus should not normally be shown to a participant during capture because it can suggest material;
- multimodal contributions such as photographs, letters, documents and objects should eventually be attachable to the conversational moment in which they arise;
- privacy is relational and must include living people mentioned by contributors;
- consent must become scoped/versioned production state rather than a single checkbox;
- production architecture needs an explicit threat model covering hostile users, automated agents, poisoning, impersonation, extraction attacks, device/server compromise and derived-data leakage.

## Production interaction direction

The intended final participant-facing system is:

- mobile-first;
- speech-first;
- very low interaction burden;
- accessible to older participants and people with varied visual, hearing, dexterity, cognitive and technical-access needs;
- full duplex.

Full duplex is a production requirement because the interaction needs to feel natural. A participant should be able to interrupt, correct the system immediately, continue after an apparent turn boundary, restart a sentence and overlap naturally.

Floor authority should be asymmetric:

- participant interruption should be easy/immediate;
- system interruption of the participant should be conservative.

The current continuous half-duplex browser loop is useful only as a disposable test path. It is not the final interaction model.

The future placement of ASR, interviewer inference and TTS remains deliberately unresolved. Fully local, trusted-remote and hybrid architectures should be compared against privacy, quality, latency, battery/thermals, connectivity, device coverage, cost and governance requirements before choosing.

## Evaluation status

The executable researcher-authored evaluation set currently covers the established prototype scenarios, including uncertainty, hearsay, correction, refusal, digression, contradiction, prompt injection and reported control speech.

`docs/MANUAL-TESTS.md` has now been expanded with additional research-derived cases for:

- suggestion resistance;
- affirmation resistance;
- multiple-question packing;
- premature closure;
- participant correction of an interviewer error;
- archive blindness/cross-session leakage;
- deferred collective significance;
- derived-summary preservation.

The broader framework in `docs/EVALUATION-FRAMEWORK.md` separates:

- conversational quality;
- capture adequacy;
- epistemic restraint;
- deferred-significance behaviour;
- full-duplex timing;
- voice fidelity;
- accessibility;
- adversarial robustness;
- representation;
- privacy/access.

It also separates evidence levels so deterministic tests and researcher-authored scenarios cannot be misreported as participant validation.

## Current voice implementation and evidence gap

The prototype voice path now uses a persistent microphone stream and can use resident `whisper-server`, removing repeated Whisper model initialisation. `.env.example` and `docs/VOICE.md` distinguish app-managed resident Whisper from an externally supervised `WHISPER_SERVER_URL`.

The current endpointing threshold is 1.7 seconds, not the older 2.4-second value that remained in stale documentation before this audit.

Still unresolved empirically:

- real 10–15-turn spoken conversation;
- whether 1.7 seconds cuts off ordinary reflective hesitation;
- real ASR behaviour on Uruguayan names, places and speech;
- first-turn/ongoing TTS latency;
- moments where half duplex prevents a natural participant interruption;
- full end-to-end latency from participant completion to audible system response.

## Remaining immediate gates

1. Run the revised conversational policy in sustained live Uruguayan-Spanish interaction and record the result.
2. Validate the small router on adversarial/natural Spanish control and testimony cases; routing errors affect whether material is treated as testimony at all.
3. Run the real 10–15-turn voice test with resident Whisper confirmed.
4. Add/inspect TTS timing so the full perceived voice latency is measured rather than inferred.
5. Run the expanded suggestion/affirmation/correction/archive-blindness/deferred-significance scenarios.
6. Keep the current prototype free of real participant testimony until the appropriate ethics/governance route exists.
7. Use the resulting evidence to design the next architecture from first principles rather than hardening prototype shortcuts.

## Production work still intentionally open

- full-duplex mobile architecture;
- local/remote/hybrid inference placement;
- consent and participant review;
- privacy and differentiated access;
- relational privacy;
- threat model and corpus-integrity controls;
- encryption/key management and secure synchronisation;
- offline/intermittent capture;
- identity/coreference governance;
- multimodal contribution model;
- final archival store and stewardship;
- actual revocation/deletion propagation;
- institutional ownership and public-access policy;
- human-participant validation in Uruguay.

## Repository boundary

Do not incrementally harden the current code into the production system by default. Prototype implementation state belongs here; publication manuscripts/reviews remain canonical in `krahd/academic-writing`; cross-repository administrative state must be kept current in `krahd/tom-work-admin` according to `WORK-ADMIN.md`.
