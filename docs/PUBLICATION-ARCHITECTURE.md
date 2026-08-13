# Publication and implementation architecture

**Status date:** 13 August 2026

This file links implementation stages to the three active/planned papers. The canonical detailed publication plan is:

`krahd/academic-writing/my_papers_2026/2026 - publication-plan/project-dossiers/collective-memory-publication-architecture.md`

## P0 — disposable discovery prototype / RTCA

Current repository state.

Primary publication role: NeurIPS 2026 RTCA short paper *Conditions of Recollection*.

P0 currently provides:

- participant-led Conversation view;
- corpus-wide `campo de memoria`;
- session-local/archive-blind interviewer context;
- first-class recollection nodes;
- weak mention relations;
- simplified label-level cross-session convergence;
- chronology preserving divergent/unlocated time expressions;
- exact source preservation and append-only audit/revision state;
- model/researcher provenance;
- constrained conversational controller;
- half-duplex local voice;
- researcher-authored/synthetic evaluation tooling.

RTCA is non-archival. Its concepts, diagrams and preliminary evidence may legitimately be developed later in the archival *Computers* article. The reason to keep RTCA narrow is conceptual clarity, not an artificial publication firewall.

Freeze/document a P0 state around RTCA submission. Do not treat P0 shortcuts as production decisions merely because they exist in code.

## P1 — Computers research architecture

Primary publication role: invited archival *Computers* extension of the IBERAMIA paper.

P1 is a **pre-deployment computational research architecture**, not the final production system.

Its defining problem is recursive distributed capture:

`archive → retrieval/model context → later conversation → human articulation/recollection → archive`

P1 should be specified from the long-lived requirements before implementation. It should prioritise:

1. capture-time versus archive-time privilege/context separation;
2. archive-blind participant-facing generation by default;
3. an explicit experimental/governed archive-informed mode where archive-derived material is recorded as mediation;
4. source / mediation / interpretation as typed, versioned, attributable objects;
5. mention-level evidence rather than label-level identity merging;
6. explicit provisional/reversible cross-session coreference and relation hypotheses;
7. preservation of uncertainty, hearsay, contradiction, correction, refusal/withdrawal and model-introduced content;
8. deterministic isolation/provenance/revision invariants;
9. reproducible archive-blind versus archive/memory-enabled multi-session experiments;
10. multi-model conversational-policy and representation-fidelity evaluation;
11. enough access/security machinery to test the exact claims made in the paper;
12. an open-source frozen release corresponding to submission.

P1 does **not** need to solve final mobile deployment, full-duplex UX, institutional stewardship, legal policy, production consent validity or participant accessibility merely for the journal article.

The P0 code may supply useful modules and lessons, but P1 should not be produced by blindly hardening P0.

## P2 — participant/deployment system

Primary publication role: later archival journal paper based on real participant and institutional evidence.

P2 is designed after P1 evidence and after human-subjects, partner, consent, privacy, stewardship and security requirements are resolved.

P2 owns:

- production participant interface;
- mobile/speech/full-duplex decisions where evidence supports them;
- operational consent/review/withdrawal;
- real access control and stewardship;
- security hardening;
- accessibility validation;
- situated deployment in Uruguay;
- real participant/corpus evidence.

The later paper should be free to show that P1 assumptions were wrong. Therefore do not prematurely encode a future empirical conclusion into P1.

## Cross-stage rules

- RTCA/P0 concepts may flow into *Computers*/P1 because RTCA is non-archival.
- The formal substantial-extension boundary is IBERAMIA → *Computers*.
- The strict second archival boundary is *Computers* → the later participant/deployment paper.
- Real participant testimony is not required to make P1 publishable and should not be consumed simply to strengthen the invited journal extension.
- False-memory literature motivates P0/P1 design and evaluation. Synthetic system tests do not establish human false-memory formation.
- The live interviewer remains archive-blind by default unless a deliberately designed condition says otherwise.
- Archive blindness in P0 currently follows from session-local context construction; P1 should make it an explicit privilege boundary that can be tested against an archive-enabled condition.
- The current `campo de memoria` is a discovery apparatus, not the P1 identity/coreference model and not collective memory itself.
