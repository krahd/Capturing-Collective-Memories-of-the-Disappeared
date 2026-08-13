# Documentation map

The project has two documentation layers.

## Long-lived design guidance

These documents guide future implementations and should survive the disposable prototype.

- [`DESIGN-FOUNDATIONS.md`](DESIGN-FOUNDATIONS.md) — project objective hierarchy, problem families, long-lived invariants and research grounding.
- [`COLLECTIVE-MEMORY-CAPTURE.md`](COLLECTIVE-MEMORY-CAPTURE.md) — deferred collective significance, under-formulated recollections, capture policy, archive blindness and cross-session representation cautions.
- [`FUTURE-ARCHITECTURE.md`](FUTURE-ARCHITECTURE.md) — mobile-first/full-duplex production direction, capture/archive isolation, source/mediation/interpretation layers, privacy, consent, accessibility, threat model and unresolved deployment choices.
- [`EVALUATION-FRAMEWORK.md`](EVALUATION-FRAMEWORK.md) — evidence levels, conversational/capture evaluation, epistemic-interference failures, deferred-significance tests, full-duplex metrics, accessibility and adversarial evaluation.

The research reviews behind these documents are maintained in `krahd/academic-writing`:

- [State of the Art Review — *The Conversation Is Not the Record*](https://github.com/krahd/academic-writing/blob/main/my_papers_2026/2026%20-%20NeurIPS%20RTCA%20-%20Collective%20Memories/STATE-OF-THE-ART-REVIEW.md)
- [Collective-memory capture review — *Conditions of Recollection*](https://github.com/krahd/academic-writing/blob/main/my_papers_2026/2026%20-%20NeurIPS%20RTCA%20-%20Collective%20Memories/COLLECTIVE-MEMORY-CAPTURE-REVIEW.md)

## Disposable-prototype documentation

These documents describe or test the implementation currently in this repository. Prototype shortcuts must not be promoted to production requirements merely because they exist in code.

- [`VOICE.md`](VOICE.md) — current local continuous half-duplex voice implementation and its limits.
- [`MANUAL-TESTS.md`](MANUAL-TESTS.md) — researcher-authored tests for current conversational and representation behaviour.
- [`TEST-REPORT.md`](TEST-REPORT.md) — evidence and observed failures from actual runs.
- [`DEMO.md`](DEMO.md) — runbook for demonstrating the current prototype.
- root [`GOAL.md`](../GOAL.md) — current implementation goal.
- root [`PROTOTYPE.md`](../PROTOTYPE.md) — disposable prototype rationale and non-goals.
- root [`STATUS.md`](../STATUS.md) — current implementation/evaluation status.

## Precedence

For questions about what the current code does, use `README.md`, `STATUS.md`, `GOAL.md`, `PROTOTYPE.md` and the prototype docs.

For questions about what the production system should become, use the long-lived design guidance above.

When the prototype conflicts with a long-lived production requirement, record the mismatch explicitly. Do not silently redefine the requirement to match a prototype shortcut.
