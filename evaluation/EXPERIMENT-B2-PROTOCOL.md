# RTCA Experiment B2: guard-aware low-injection repair

## Purpose

Experiment B2 follows the frozen Experiment B run after the adversarial audit showed that the deferred-significance condition achieved high automatic preservation largely through deterministic fallback replacement. B2 tests whether the architecture can preserve the contamination advantage while recovering useful conversational facilitation.

## Scientific question

Can a guarded deferred-significance policy produce a safe, contextually grounded intervention without collapsing to a generic fallback when its first model proposal is rejected?

## Frozen elements

B2 must retain, unless explicitly versioned otherwise:

- the same five researcher-authored deferred-significance scenarios;
- the same three-model panel;
- five repetitions per model/scenario cell;
- the same Ollama serving stack;
- temperature 0.7, top-p 0.8 and max_tokens 256;
- future B/C sessions withheld during generation;
- the same deterministic `guard_interview_move` function for final admission;
- exact raw outputs for every attempt.

This yields 75 primary decisions: 5 scenarios × 3 models × 5 repetitions. Each decision may contain up to three model attempts.

## Single entry point

From the repository root, after pulling the latest `main`:

```bash
python -m scripts.run_rtca_experiment_b2
```

The command prepares the frozen Ollama model matrix if necessary, runs all 75 B2 decisions, permits at most two guard-aware repair attempts after the initial candidate, applies the production deterministic guard to every candidate, falls back only after all three candidates fail, and writes the complete evidence bundle under:

```text
evaluation/results/rtca-experiment-b2-<timestamp>/
```

The bundle contains:

- `manifest.json`;
- `experiment-b2.json`, containing the complete matrix and every attempt;
- `automatic-summary.json`;
- `automatic-summary.md`;
- one `models/<model-id>/experiment-b2.json` per model;
- one `models/<model-id>/experiment-b2-manual-review.csv` per model.

The manual-review CSVs retain all attempts as JSON and reserve explicit fields for semantic distortion, premature redirection, over-specification, question packing, floor closure, facilitation, inserted noise, and reviewer notes.

## Condition

B2 runs only the deferred-significance policy. It is a follow-up diagnostic, not a replacement for the three-policy B1 comparison.

For each participant turn:

1. Generate a first deferred-significance candidate.
2. Apply the deterministic project guard.
3. If accepted, deliver it.
4. If rejected, request a new candidate from the same model while preserving the original participant turn and the frozen deferred-significance policy.
5. The retry message may state only that the previous intervention did not meet the conversational protocol and must be replaced. It must not expose withheld future sessions or an evaluator-labelled target.
6. Permit at most two repair retries after the initial candidate.
7. If all three candidates are rejected, use the existing deterministic safe fallback.

The model must never see future sessions, automatic evaluation labels, or the future target relation.

## Required retained fields

Every B2 result must retain:

- model identifier;
- scenario and repetition;
- participant turn;
- withheld later sessions, stored only for post-hoc evaluation;
- all raw model responses in order;
- all parsed candidate moves and utterances;
- guard outcome for every attempt;
- attempt count;
- final delivered move and utterance;
- whether the final delivery was model-generated or deterministic fallback;
- per-attempt and total round-trip latency;
- parse/request errors;
- scenario, policy, model-matrix and code-version provenance.

## Primary outcomes

The central B2 outcomes are:

- **guard acceptance without fallback**;
- **final fallback rate**;
- **attempt count to acceptance**;
- **delivered-intervention diversity**;
- **question packing**;
- **over-specification**;
- **uncertainty/hearsay hardening**;
- **semantic distortion**, including colloquial/dialect misinterpretation;
- **facilitates recollection** under manual adjudication;
- **inserts informational noise** under manual adjudication;
- **low-injection facilitation**: admitted, facilitates recollection, and inserts no informational noise.

## Critical semantic stress case

The existing `place-bar` case must be retained because Qwen3-4B interpreted `caía por el bar` literally as physical falling. B2 must explicitly record this as a semantic/dialect distortion when it occurs. Structural grounding is not sufficient if the model misunderstands the source expression.

## Success criterion

B2 supports an 8-page empirical-paper expansion only if all of the following hold:

1. final fallback rate is materially lower than B1 for at least the primary model and does not remain near-total across the panel;
2. the reduction in fallback does not produce a compensating rise in contamination, packed questions, epistemic hardening or semantic distortion;
3. manual adjudication shows that a meaningful proportion of delivered interventions facilitate recollection rather than merely yielding the floor;
4. the effect is not entirely dependent on a single model family;
5. all failures, including dialect and guard-repair failures, remain reported rather than removed from the dataset.

If these conditions are not met, the four-page short-paper framing remains preferable and Experiment B/B2 should be reported as evidence of the difficulty of simultaneously achieving epistemic restraint and active elicitation.

## Interpretation boundary

B2 remains a researcher-authored synthetic benchmark. It can characterise model-policy-guard behaviour and contamination opportunities. It cannot establish that human false memories are prevented, that participants remember more, or that the resulting historical record is more truthful.
