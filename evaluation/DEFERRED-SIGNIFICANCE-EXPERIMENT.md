# Deferred-significance experiment

**Purpose:** operationalise the RTCA paper's proposed retrospective cross-session evaluation without overstating what can be established before participant work.

This protocol separates two evidence levels.

## Experiment A — mechanical preservation and retrospective emergence

**Evidence level:** 0.  
**Runs anywhere:** yes.  
**Requires an LLM:** no.

Run:

```bash
python scripts/run_deferred_significance_experiment.py
```

Inputs are the researcher-authored cases in `evaluation/deferred-significance-scenarios.json`. Outputs are written to:

- `evaluation/results/deferred-significance-latest.json`;
- `evaluation/results/deferred-significance-latest.md`.

The run has three components.

### A1. Preservation-before-interpretation

For each convergence case, session A is created with only the participant source turn. The benchmark verifies that the recollection node exists before any extracted target node exists. Only then are researcher-authored derived items added.

This establishes a mechanical property of the implementation: source preservation does not depend on successful or immediate interpretation.

### A2. Deferred cross-session emergence

Sessions B and C are added after A. They independently mention the same exact-normalised target label. After each addition the benchmark rebuilds the corpus-wide memory field and measures how many conversations reach that target.

The required trajectory is `[1, 2, 3]`: the relation is not available at A capture time and becomes visible only as later sessions are added.

The source SHA-256 of A is recorded before and after later sessions are added. A passing case requires byte-for-byte identity of the source text.

This does **not** establish historical identity or truth. Exact-label recurrence is only a mechanically visible relation that may deserve later attention.

### A3. Non-collapse and controller guard probes

The benchmark checks that:

- contradictory dates remain separate;
- unlocated temporal expressions remain represented as undated rather than receiving invented dates;
- uncertainty remains attached to the recollection;
- multiple-question packing is rejected by the deterministic interview guard;
- unsupported specificity is rejected;
- generic `ACKNOWLEDGE` is rejected when it is not grounded in the participant turn;
- a content-grounded acknowledgement can pass;
- a minimal floor-yielding invitation can pass;
- one grounded probe can pass;
- certainty hardening of an uncertain statement is rejected;
- immediate repetition of the same backchannel is rejected.

These guard probes were added after integrating the deployed InterviewBot findings. They test implemented protections related to question density, generic acknowledgement, grounding and premature narrowing. They do not show what a model will choose to generate.

## Experiment B — live model retrospective action audit

**Evidence level:** 1.  
**Requires an LLM:** yes.  
**Participant data:** none.

Experiment B is the paper-facing model experiment. It should use the same researcher-authored session-A fragments while withholding B/C from the model during capture.

### Conditions

Use the same exact conversational model and decoding configuration under three policy conditions:

1. **Immediate-information policy** — prioritises present information gain and asks a specific question when a potentially resolvable entity, place or date appears.
2. **Adaptive semi-structured policy** — follows conventional contextual interviewing criteria: necessary, open, grounded, one probe at a time.
3. **Deferred-significance policy** — the project's current constrained policy: source is preserved first; the interviewer may ask, acknowledge or yield, but present relevance must not become an irreversible editorial decision.

The baseline policies are experimental comparators. They must not be represented as implementations of any particular published system unless their prompts are directly reproduced under the relevant licence and protocol.

### Procedure

For every scenario family:

1. Start from a fresh conversation containing session A only.
2. Run the policy/model without access to B or C.
3. Preserve the exact generated move, utterance, router outcome, guard outcome, model identifier, endpoint and sampling configuration.
4. Do not retry selectively. If repetitions are used, fix the count before running and retain every output.
5. After the A response has been frozen, reveal B and C only to the evaluator.
6. Audit the A action retrospectively against the later relation.

### Primary outcome: possibility preservation

Score the A intervention on four binary failure mechanisms:

- **premature redirection:** moves away from the participant's fragment before they can continue it;
- **over-specification:** introduces specificity or a candidate relation absent from A;
- **question packing:** asks more than one distinct thing;
- **floor closure:** treats a brief/uncertain fragment as exhausted rather than allowing continuation.

The primary per-run outcome is whether **none** of the four mechanisms occurs.

This is intentionally stricter than generic conversational quality. A fluent, polite response can still fail.

### Secondary outcomes

Record:

- move type (`BACKCHANNEL`, `INVITE_CONTINUE`, `ACKNOWLEDGE`, `FOLLOW_UP`, `CLARIFY` or comparator equivalent);
- number of distinct probes, not question marks;
- whether acknowledgement is content-grounded;
- whether uncertainty/hearsay is preserved;
- response length;
- whether a later-significant noun phrase remains available for participant continuation;
- guard acceptance/fallback for the project's policy.

Runtime metrics such as TTFT remain a separate evidence layer. They must not be combined with possibility-preservation scores.

### Repetitions

For a workshop-scale result, use at least 5 repetitions per scenario × policy condition if inference cost permits. With 5 convergence scenarios and 3 policies this yields 75 A-turn decisions. Ten repetitions yields 150.

The unit of analysis is the generated intervention, nested within scenario and policy. Do not treat repetitions as independent human observations.

### Analysis

Report raw counts and proportions first. For a small researcher-authored benchmark, avoid inferential-statistical theatre. If the sample is expanded enough to justify modelling, use a mixed-effects logistic model with policy as fixed effect and scenario as a grouping factor, but retain the raw contingency table.

### Required provenance

Freeze:

- repository commit;
- exact scenario file hash;
- exact prompt/policy text for each condition;
- exact model identifier and weights/provider identity;
- quantisation/precision;
- context size;
- temperature/top-p/max tokens;
- server/runtime and launch command;
- every raw output.

## What can be claimed after Experiment A only

Experiment A can support statements such as:

- the implementation stores the recollection before interpretation;
- later sessions can make an exact-label cross-session relation visible without rewriting the earlier source;
- tested contradictions and uncertainty remain represented;
- the deterministic guard rejects the tested packed, unsupported, ungrounded, certainty-hardening and repetitive interventions.

It cannot support statements that the LLM reliably behaves this way in conversation.

## What can be claimed after Experiment B

A complete Experiment B can support narrow statements about the tested model + policy + researcher-authored scenarios, for example that one policy produced fewer branch-closing interventions than another under the frozen benchmark.

It still cannot establish effects on human memory, participant trust, cultural validity, trauma-informed practice or field effectiveness.
