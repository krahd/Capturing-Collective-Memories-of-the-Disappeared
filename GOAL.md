# Current implementation goal

Implement and test the disposable prototype described in `PROTOTYPE.md`.

The prototype is an experimental instrument for the larger project whose central objective is to capture collective memories of Uruguay's detained-disappeared. Long-lived design requirements are now recorded under [`docs/README.md`](docs/README.md), especially [`docs/DESIGN-FOUNDATIONS.md`](docs/DESIGN-FOUNDATIONS.md), [`docs/COLLECTIVE-MEMORY-CAPTURE.md`](docs/COLLECTIVE-MEMORY-CAPTURE.md), [`docs/FUTURE-ARCHITECTURE.md`](docs/FUTURE-ARCHITECTURE.md) and [`docs/EVALUATION-FRAMEWORK.md`](docs/EVALUATION-FRAMEWORK.md).

The current prototype consists of:

1. **Conversation view** — a sustained, natural, participant-led conversational interaction designed for adult native speakers of Uruguayan Spanish, in text or in fully local continuous half-duplex voice.
2. **Campo de memoria** — the structure that many conversations accumulate into, drawn as one graph across all of them and grown automatically as people speak, with recollections as first-class nodes and no annotation controls on screen.

The earlier plan called the second view a **conversation workbench**: a researcher apparatus of selection, annotation, status labels and manual extraction. Those operations still exist in the API, the data model and the exports, but putting them on screen communicated bureaucracy rather than accumulation, and made the interesting claim — that partial recollections can later become related without being collapsed into canonical facts — impossible to see. The interface therefore shows the accumulated field instead, and extraction runs by itself behind each testimony turn.

The memory field is a research/demo apparatus. It is not a claim that the graph itself is collective memory, and its current string-normalised node convergence is not a production identity-resolution method.

## Definition of done

The current prototype goal is done when:

- the prototype runs locally from documented setup instructions, with no network;
- the conversation can sustain realistic multi-turn exchanges in natural Uruguayan Spanish without becoming a questionnaire;
- the interaction follows digressions, corrections, refusals, uncertainty, and topic returns plausibly;
- a turn can be spoken and answered aloud without anything leaving the machine;
- the transcript is preserved exactly;
- derived material remains explicitly provisional, attributable to whoever or whatever produced it, and traceable to source turns;
- the memory field grows from conversation without curation, keeps disagreement rather than resolving it, and never asserts more than the extraction supports;
- at least one view the accumulated material can produce is actually built, rather than only named;
- sessions export to JSON and Markdown;
- deterministic behaviour has automated tests, including adversarial cases where testimony resembles a control instruction;
- a documented manual test suite includes several researcher-authored Uruguayan-Spanish scenarios;
- the test round produces a concrete list of interaction and architectural requirements for the eventual production system.

The prototype code is disposable. No architectural decision in this phase is presumed to survive into the production system.

In particular, the current half-duplex desktop/browser voice path is not the production interaction target. The current production direction is mobile-first, speech-first and full duplex, with participant interruption easy and system interruption conservative. That future requirement belongs to the design documents rather than to the definition of done for this prototype.
