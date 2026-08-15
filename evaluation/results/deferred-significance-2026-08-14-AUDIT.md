# Deferred-significance experiment audit — 14 August 2026

## Scope

Audit of the Level-0 retrospective cross-session benchmark introduced for *Conditions of Recollection*, including its scenario design, first execution, failure diagnosis, corrected execution, retained results and claim boundary.

## Execution trail

1. The first attempted workflow execution failed before the benchmark because the runner was invoked as a file and could not import repository-root modules (`ModuleNotFoundError: controller`). The invocation was corrected to `python -m scripts.run_deferred_significance_experiment`.
2. The next diagnostic execution ran the benchmark and returned **14/16**. All five convergence and all three non-collapse cases passed. Two intended positive guard probes were rejected.
3. Inspection showed that both positive probes reused a source containing `le decían Tito`. The controller correctly classifies `decían` as an attribution/hearsay marker and therefore requires the intervention to preserve epistemic distance. The benchmark had inadvertently expected a direct grounded acknowledgement/probe to pass against an attributed source. This was a benchmark-design error, not evidence that the controller lacked grounding support.
4. The positive acknowledgement/probe controls were therefore moved to a separate direct source (`Conocí a Tito en el barrio y a veces venía por casa.`). Negative hearsay-sensitive cases were not weakened.
5. Final workflow run `31856109446`, source commit `06eac0f4e74f745684c6f7d24c648b78f580d5ba`, passed. Main repository CI run `31856109506` on the same commit also passed.

The failed intermediate result was retained as diagnostic evidence rather than silently discarded. Diagnostic artifact from run `31856005839`: `9239036590`.

## Final-result verification

Final artifact: `9239068474`  
Artifact ZIP SHA-256: `5216bd0754c2625bebaa11c2cba7fa0470755120ae4a7a9f66f9f7cd042f2a4e`

The downloaded artifact was compared against the workflow log. Both report:

- 16 total checks;
- 16 passed, 0 failed;
- convergence 5/5;
- non-collapse 3/3;
- controller guards 8/8;
- benchmark pytest 2/2.

For every convergence case, the target-conversation trajectory is `[1, 2, 3]`; `recollection_exists_before_interpretation=true`; `target_exists_before_interpretation=false`; and the session-A source SHA-256 is identical before and after adding later sessions.

The retained JSON in `evaluation/results/deferred-significance-2026-08-14.json` reproduces the final artifact and adds only a `provenance` object containing workflow/run/artifact identifiers and the local research date. The retained Markdown report is a human-readable synthesis of the same evidence.

## Design audit

### What the benchmark establishes

The convergence test is a legitimate mechanical test of the architecture's temporal ordering: participant source can exist before derived interpretation, and a corpus relation can become visible only after later sessions are incorporated without rewriting the earlier source.

The non-collapse cases directly test three stated representation invariants: contradictory datings, unresolved time and uncertainty.

The guard probes provide deterministic regression coverage for behaviours made especially salient by InterviewBot: question packing, generic acknowledgement, grounding and repetitive backchannels. They also cover unsupported specificity and certainty hardening.

### What the benchmark does not establish

The benchmark supplies its derived items itself. It therefore does not evaluate extraction accuracy or entity resolution.

The repeated relation is exact-normalised label identity. It does not establish that two mentions refer to the same historical person/place/object, and it must not be described as verification.

The guard probes test acceptance/rejection of researcher-authored candidate moves. They do not test which move the language model will generate.

The benchmark contains no participant data and cannot establish effects on recollection, trust, usability, cultural validity, trauma-informed practice or archival adequacy.

### Residual methodological limitation

The five convergence scenarios currently all use a clean three-session exact-label recurrence. This is appropriate for testing the implementation invariant, but too easy to stand alone as evidence about conversational policy. The Level-1 experiment should therefore include lexical variation, irrelevant distractors, ambiguous recurrence and cases where the later material does **not** make A significant, so that a policy cannot score well merely by always yielding.

## Audit conclusion

**Mechanical benchmark: PASS.** The final Level-0 result is reproducible, retained and correctly bounded.

**Paper-facing behavioural experiment: NOT YET ESTABLISHED by this run.** The next evidentiary step is the documented Level-1 policy comparison against a frozen live model. Until that is run, the RTCA manuscript should report this result only as implementation/evaluation-harness evidence, not as evidence that the conversational policy preserves future-significant material better than an alternative policy.
