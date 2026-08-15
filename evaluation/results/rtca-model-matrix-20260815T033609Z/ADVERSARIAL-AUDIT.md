# RTCA Experiment B adversarial audit

**Frozen source run:** `22cfffb4f5fd6f23fb9765823a050b1b2a20272c`

**Enriched adjudication commit:** `deed0674f83e37f2307744a721ee18237d1ca4d3`

## Scope

This audit examines the researcher-authored synthetic model-policy experiment only. It does not measure human recollection, participant experience, false-memory formation, or historical truth. The purpose is to determine whether the apparent safety advantage of the deferred-significance policy represents useful low-injection elicitation, or whether it is largely produced by guard replacement and conversational collapse.

## Mechanical integrity

The source run completed all 225 planned model decisions with no request failures. Level-0 checks passed 16/16. The three models, three policy conditions, five scenarios and five repetitions per cell were retained as frozen experimental evidence.

## Automatic headline

The automatic screen reports possibility-preservation rates of 38.7% for immediate-information, 49.3% for adaptive semi-structured and 94.7% for deferred significance across the three models. That headline must not be treated as successful elicitation without inspecting the guard path.

## Guard-path finding

### Qwen3-30B-A3B primary

All 25 deferred-significance outputs are rejected by the deterministic guard and replaced by the fallback `Contame.`: **25/25 fallback, 100%**.

The raw proposals are not uniformly unsafe in the same way. Typical proposals include content-bearing acknowledgements such as `Sí, Tito, a veces aparecía por casa.` and generic acknowledgements such as `Entiendo.`. The guard correctly rejects agreement-like `Sí` acknowledgements and acknowledgements that fail to preserve epistemic distance. Nevertheless, the delivered condition has collapsed to a single repeated utterance.

Interpretation: this cell demonstrates architectural restraint, but not useful low-injection facilitation.

### Qwen3-4B scale control

The deferred-significance condition falls back in **20/25 cases, 80%**. The five accepted cases are all in the `place-bar` scenario and ask variants of `¿Podrías decirme más sobre cómo caía por el bar de la esquina?`.

This is a serious dialect/pragmatics failure: the Rioplatense expression `caía por el bar` is interpreted as physical falling. The current guard accepts the questions because they are lexically grounded and structurally compliant. Therefore lexical grounding plus question-shape constraints are insufficient to guarantee semantic non-distortion.

Interpretation: the scale-control model exposes a model-dependent cultural-linguistic failure that the deterministic guard does not catch.

### Mistral Small 3.2 cross-family control

The deferred-significance condition falls back in **18/25 cases, 72%**. The seven accepted cases are mostly minimal backchannels or acknowledgements (`mm`, `Ajá`, `Ahá`, `Ah, sí`, `Ah, una radio Spika.`), rather than substantive grounded facilitation.

Interpretation: the cross-family model avoids total fallback collapse, but the accepted outputs still provide little evidence that the condition can actively elicit recollection without adding information.

## Consequence for the 94.7% preservation result

The 94.7% automatic preservation rate is real as a measurement of the **delivered post-guard surface**, but it is not evidence that the model-policy combination itself has learned high-quality elicitation. It is strongly mediated by fallback replacement:

- Qwen3-30B: 100% deferred fallback;
- Qwen3-4B: 80% deferred fallback, with the accepted remainder containing a dialectic semantic error;
- Mistral Small 3.2: 72% deferred fallback, with accepted outputs largely minimal backchannels.

The correct claim is therefore narrower: **the architecture can suppress many contamination opportunities, but the present implementation often does so by replacing model output with minimal floor-yielding language.**

## Baseline findings that survive the audit

The baseline policies exhibit substantive failure mechanisms that are not artefacts of the automatic evaluator:

- categorical narrowing of an uncertain identity (`¿Era un familiar, un amigo o alguien más?`);
- requests for unavailable specificity such as names, exact locations or dates;
- question packing;
- conversion of hearsay or uncertainty into flatter assertions;
- model-dependent misreading of colloquial Rioplatense language;
- repeated generic acknowledgement patterns.

These remain useful evidence for the paper because they show concrete ways in which a conversational system can alter the conditions under which a recollection develops.

## Manual-adjudication status

The enriched review CSVs now retain raw move, raw utterance, guard outcome, delivered move and delivered utterance. The `human_*` columns remain intentionally unfilled. A complete human-coded 225-row adjudication should not be simulated from automatic heuristics; the structural findings above are already decisive enough to determine the next experimental step.

## Decision

Experiment B should be preserved as a frozen diagnostic run, not rewritten or discarded. It demonstrates three important facts:

1. prompt-level restraint is strongly model-dependent;
2. deterministic guards materially change delivered behaviour;
3. a fail-closed guard can create conversational collapse, so safety cannot be evaluated independently of facilitation quality.

A follow-up Experiment B2 is required before promoting the workshop submission to an 8-page empirical full paper. B2 should test whether guard-aware repair can reduce fallback collapse while retaining the contamination advantage.
