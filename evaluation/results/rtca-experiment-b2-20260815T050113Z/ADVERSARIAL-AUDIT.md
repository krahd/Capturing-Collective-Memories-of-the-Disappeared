# RTCA Experiment B2 adversarial audit

**Frozen B2 source run:** `c64fe5387dfe807b564437fb2a9e160561aea28c`

**B1 comparison source:** `evaluation/results/rtca-model-matrix-20260815T033609Z/ADVERSARIAL-AUDIT.md`

## Scope

This audit examines the researcher-authored synthetic B2 run only. It does not measure human recollection, participant experience, false-memory formation, or historical truth. Its purpose is to determine whether guard-aware regeneration recovers useful low-injection facilitation after the B1 audit showed that the deferred-significance condition often achieved restraint through deterministic fallback.

## Mechanical result

B2 completed all 75 planned primary decisions across the three frozen models, five scenarios and five repetitions. Each decision allowed one initial candidate plus up to two guard-aware repair attempts. The future sessions remained withheld from generation.

The automatic fallback result changed sharply relative to B1:

| Model | B1 deferred fallback | B2 final fallback | Change |
|---|---:|---:|---:|
| Qwen3-30B-A3B | 25/25 (100%) | 1/25 (4%) | -96 pp |
| Qwen3-4B | 20/25 (80%) | 5/25 (20%) | -60 pp |
| Mistral Small 3.2 | 18/25 (72%) | 2/25 (8%) | -64 pp |

Guard-aware repair therefore works mechanically: it can often obtain an admissible model-generated intervention rather than immediately collapsing to the deterministic fallback.

That result is necessary but not sufficient. The substantive question is what kind of intervention becomes admissible.

## Qwen3-30B-A3B primary

The automatic headline is superficially excellent: 24/25 decisions are accepted without deterministic fallback, with no packed final questions and no automatic uncertainty hardening. However, the qualitative surface still collapses.

Across all 25 final deliveries:

- 22 are minimal backchannels such as `Mm.`, `Mm-hm.`, `Mm-hmm.` or `Mmm.`;
- 2 are brief acknowledgements of the radio case (`Entiendo, siempre estaba prendida.` / `Entiendo, siempre prendida.`);
- 1 is the deterministic fallback `Contame.`;
- no final intervention is a substantive grounded question.

The repair trajectory is highly regular. The model commonly proposes an agreement-like acknowledgement on attempt 1, a more active but guard-incompatible prompt on attempt 2, and then retreats to a minimal backchannel on attempt 3. Mean attempt count is 2.92, and no item is accepted on the first attempt.

This is not the same failure as B1, because the final surface is model-generated rather than deterministic fallback. But interactionally it is close to the same equilibrium: **the easiest way for the model to satisfy the guard is to say almost nothing.**

Interpretation: B2 fixes fallback collapse for the primary model without yet demonstrating active low-injection elicitation.

## Qwen3-4B scale control

Qwen3-4B behaves very differently. It accepts 20/25 decisions without fallback and frequently converges on content-bearing clarifications rather than backchannels. This is the strongest evidence in B2 that repair can recover active facilitation.

Several outputs are plausibly useful and epistemically careful. In the hearsay `Flaco` case, for example, repaired questions explicitly retain attribution to the participant's mother, such as `¿Cómo decía tu vieja que aparecía por casa?`. This is substantially better than prompting the participant as if the recollection were first-hand.

However, the same model reproduces the critical semantic failure from B1. In all five `place-bar` trials, the guard accepts variants of `¿Podrías decirme más sobre cómo caía por el bar de la esquina?`. The Rioplatense `caía por` is again treated as if `caer` were the recollective object rather than an idiom meaning to drop by / turn up. The intervention is lexically grounded and structurally compliant while semantically distorting the participant's utterance.

The radio and Sunday-meeting cases also tend towards clarification questions that may be conversationally productive but sometimes over-demand specification (`qué era la radio Spika`, `qué tipo de reuniones`, `qué sucedía`). Automatic screening already flags seven over-specification cases and four packed-question cases across the model's 25 decisions.

Interpretation: the 4B scale control recovers active elicitation, but at a meaningful semantic and pragmatic cost. It demonstrates why guard compliance cannot be treated as semantic fidelity.

## Mistral Small 3.2 cross-family control

Mistral reduces fallback from 72% in B1 to 8% in B2, but most accepted outputs remain minimal interactional signals: `Ajá`, `Mm`, `Mmm`, `Hmm`, `Ah, interesante`, `Ah, sí`, or a short repetition. The model occasionally emits an open invitation such as `Cuéntame.`, but there is little evidence of sustained contextually grounded probing.

The automatic evaluator also flags twelve over-specification cases and six generic acknowledgements. Some of those automatic flags are conservative and require manual adjudication, but the dominant qualitative pattern is already clear: repair improves admission without reliably producing richer elicitation.

Interpretation: the cross-family control supports the robustness of the architectural restraint result, but not a claim that repair generally yields active low-injection facilitation.

## What B2 establishes

B2 improves the architectural result in an important way. The fail-closed system need not immediately replace rejected model output with a fixed fallback. A simple repair loop can sharply reduce deterministic fallback across model families.

But B2 also exposes a second-order optimisation problem. Once the model is told only that a candidate failed the protocol, it often converges towards the easiest admissible region of the response space. For the primary 30B and Mistral models, that region is dominated by minimal backchannels. For Qwen3-4B, the model remains more active, but its active responses include a repeated dialect-semantic distortion that the guard cannot detect.

The stronger claim supported by B1+B2 is therefore:

> **Epistemic restraint is not a scalar property of an interviewer. Tightening admission constraints can move a system between different failure modes: informational injection, deterministic fallback, interactional minimalism, or semantically distorted but structurally admissible probing.**

This is a more useful result than claiming that the deferred-significance policy simply “wins”. It shows that the real-time action problem is not solved by prompt restraint or a deterministic guard alone.

## Paper-form decision

B2 does **not** meet the pre-registered threshold for promoting the RTCA submission to an 8-page empirical full paper.

It satisfies the first success condition: final fallback is materially lower across the panel. It does not yet satisfy the third condition strongly enough: the primary model and cross-family control mostly recover admissibility through minimal backchannels rather than clearly useful elicitation. The 4B model produces more active probing, but the recurring `caía por el bar` distortion prevents treating that activity as an unqualified success.

The 4-page short paper therefore remains the stronger submission form.

B1 and B2 should be used selectively in that paper to support three concrete points:

1. guard-mediated restraint can suppress contamination opportunities;
2. fail-closed restraint can collapse interaction, and repair can reduce deterministic fallback without necessarily recovering facilitation;
3. lexical grounding and formal protocol compliance do not guarantee semantic fidelity, especially under dialectal or culturally specific language.

The full B1/B2 evidence should remain available as project documentation and as material for the later, larger architecture/evaluation paper.

## Manual-adjudication status

The B2 review CSVs retain dedicated human fields for semantic distortion, facilitation and inserted informational noise. Those fields remain unfilled. This audit makes a conservative qualitative judgement from the final interventions and repair traces; it is not a substitute for a formally coded 75-row adjudication with an explicit codebook and, ideally, more than one rater.

For the RTCA short-paper decision, the structural findings are already decisive enough that completing a formal adjudication is not required before choosing the four-page format. If B2 is reported quantitatively beyond fallback/attempt statistics, the human-coded review should be completed first.
