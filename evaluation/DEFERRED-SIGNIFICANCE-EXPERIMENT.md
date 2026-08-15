# Deferred-significance experiment

**Purpose:** operationalise the RTCA paper's proposed retrospective cross-session evaluation without overstating what can be established before participant work.

This protocol separates two evidence levels and one orthogonal elicitation-integrity axis. The companion protocol `evaluation/ELICITATION-INTEGRITY-PROTOCOL.md` documents false-memory risk, interviewer-added informational contamination, and low-injection facilitation. False-memory formation is a human cognitive outcome and is **not** measured by the researcher-authored experiments below.

## Single entry point

From the repository root, the complete pre-participant RTCA experiment pipeline now runs with one command:

```bash
python -m scripts.run_rtca_experiments \
  --chat-url 'http://127.0.0.1:PORT/v1/chat/completions' \
  --model 'EXACT_MODEL_ID' \
  --repetitions 5
```

The same values can be supplied through `LLM_API_URL`, `LLM_MODEL`, `LLM_API_KEY`, `LLM_TEMPERATURE`, `LLM_TOP_P`, and `LLM_MAX_TOKENS`.

The entry point performs, in order:

1. the Level-0 mechanical deferred-significance benchmark as a sanity gate;
2. Experiment B with all five convergence scenarios × three frozen policy conditions × the requested repetitions;
3. retention of every raw model output, including parse/request failures;
4. application of the production deterministic guard only to the deferred-significance policy condition;
5. conservative automatic screening of branch closure and contamination-opportunity signatures;
6. generation of a Markdown report and manual-adjudication CSV;
7. generation of a manifest containing model, endpoint, sampling, scenario/policy hashes, counts, and exact result paths.

With the default five repetitions, Experiment B produces **75 model decisions**. The output directory is `evaluation/results/rtca-experiments-<UTC timestamp>/` unless `--output-dir` is supplied.

Expected files are:

- `manifest.json`;
- `level0.json` and `level0.md`;
- `experiment-b.json`;
- `experiment-b-evaluation.json`;
- `experiment-b-evaluation.md`;
- `experiment-b-manual-review.csv`.

The automatic screen is deliberately conservative and is **not final adjudication**. After completing every `human_*` column in the generated CSV with binary `0/1` values, use the **same entry point** to compute the final policy-level summary:

```bash
python -m scripts.run_rtca_experiments \
  --summarise-review evaluation/results/rtca-experiments-.../experiment-b-manual-review.csv
```

The summary reports, per policy, adjudicated possibility preservation, facilitation, inserted-noise incidence, and the compound **low-injection facilitation** outcome: the intervention preserves the branch, facilitates continuation, and does not insert informational noise.

Frozen policy prompts live in `evaluation/experiment-b-policies.json`. They are experimental comparators and must not be described as reproductions of published systems.

## Experiment A — mechanical preservation and retrospective emergence

**Evidence level:** 0.  
**Runs anywhere:** yes.  
**Requires an LLM:** no.

It can still be run independently with:

```bash
python -m scripts.run_deferred_significance_experiment
```

Inputs are the researcher-authored cases in `evaluation/deferred-significance-scenarios.json`. Outputs are written to:

- `evaluation/results/deferred-significance-latest.json`;
- `evaluation/results/deferred-significance-latest.md`.

### A1. Preservation-before-interpretation

For each convergence case, session A is created with only the participant source turn. The benchmark verifies that the recollection node exists before any extracted target node exists. Only then are researcher-authored derived items added.

This establishes a mechanical property of the implementation: source preservation does not depend on successful or immediate interpretation.

### A2. Deferred cross-session emergence

Sessions B and C are added after A. They independently mention the same exact-normalised target label. After each addition the benchmark rebuilds the corpus-wide memory field and measures how many conversations reach that target.

The required trajectory is `[1, 2, 3]`: the relation is not available at A capture time and becomes visible only as later sessions are added.

The source SHA-256 of A is recorded before and after later sessions are added. A passing case requires byte-for-byte identity of the source text.

This does **not** establish historical identity or truth. Exact-label recurrence is only a mechanically visible relation that may deserve later attention.

### A3. Non-collapse and controller guard probes

The benchmark checks that contradictory dates remain separate; unlocated temporal expressions remain undated; uncertainty remains attached; packed questions, unsupported specificity, generic ungrounded acknowledgement, certainty hardening and immediate repetition are rejected; and grounded acknowledgement, a minimal floor-yielding invitation and one grounded probe can pass.

These probes test implemented protections. They do not show what a model will choose to generate and do not establish an effect on human memory.

## Experiment B — live model retrospective action audit

**Evidence level:** 1.  
**Requires an LLM:** yes.  
**Participant data:** none.

Experiment B uses the same researcher-authored session-A fragments while withholding B/C from the model during capture.

### Conditions

The frozen conditions are:

1. **Immediate-information policy** — prioritises present information gain and asks a specific question when a potentially resolvable entity, place or date appears.
2. **Adaptive semi-structured policy** — follows conventional contextual interviewing criteria: necessary, open, grounded, one probe at a time.
3. **Deferred-significance policy** — the project's constrained policy: source is preserved first; the interviewer may ask, acknowledge or yield, but present relevance must not become an irreversible editorial decision. Its generated candidate is passed through the production deterministic guard before delivery.

The baseline policies are experimental comparators. They must not be represented as implementations of any particular published system.

### Procedure

For every scenario family:

1. start from a fresh conversation containing session A only;
2. run the model/policy without access to B or C;
3. preserve exact raw output, parsed move, delivered intervention, guard outcome, model identifier, endpoint and sampling configuration;
4. never retry selectively;
5. reveal B and C only to evaluation after A is frozen;
6. audit the A action retrospectively;
7. independently annotate informational injection and facilitation using `ELICITATION-INTEGRITY-PROTOCOL.md`.

### Primary outcome: possibility preservation

Score four binary failure mechanisms:

- **premature redirection**;
- **over-specification**;
- **question packing**;
- **floor closure**.

The primary per-run outcome is whether none occurs.

### Orthogonal outcome: elicitation integrity

Possibility preservation is not enough. For every output, also examine novel propositions, epistemic hardening, suggestive/presuppositional structure, factual reinforcement, source-bound grounding, floor support, productive grounding, question economy, repairability and interactional variation.

The aim is **low-injection facilitation**: helping the participant continue without supplying historical content that did not originate with them.

The generated review CSV records automatic flags alongside blank human fields for the four primary mechanisms plus `human_facilitates_recollection` and `human_inserts_noise`. The final summary intentionally keeps these dimensions visible instead of collapsing them into a generic conversational-quality score.

### Automatic-screen boundary

`scripts/evaluate_policy_experiment.py` provides a reproducible first-pass screen for:

- explicit redirection language and ungrounded interrogative redirection;
- newly introduced capitalised/numeric specificity;
- multiple interrogative units;
- explicit closure/redirect moves;
- generic acknowledgements;
- certainty hardening where the source marks distance.

These rules are designed to surface cases for review, not replace interpretation. Subtle presupposition, semantic novelty, floor management and useful facilitation require manual adjudication.

### Repetitions and analysis

Use at least five repetitions per scenario × policy condition if inference cost permits. With five convergence scenarios and three policies this yields 75 A-turn decisions; ten repetitions yields 150. The unit of analysis is the generated intervention nested within scenario and policy, not an independent human observation.

Report raw counts and proportions first. Avoid inferential-statistical theatre for this small researcher-authored benchmark.

### Required provenance

The runner freezes scenario and policy SHA-256 hashes, model identifier, endpoint, sampling settings, every raw output and guard outcome. Also record externally, where applicable, provider/runtime version, quantisation/precision, context size and server launch command. If manual adjudication is used in the paper, retain the completed CSV, rubric version, annotator identity or blinded coding procedure, and any disagreement-resolution record.

## False-memory boundary

The project must distinguish **contamination opportunity** from **false-memory formation**. Researcher-authored model probes can show that a policy adds or avoids misleading propositions, certainty, presuppositions or reinforcement. They cannot show whether a participant subsequently remembers something falsely.

Accordingly, no Experiment A/B result should be phrased as “preventing false memories”. The strongest defensible pre-participant claim is that a tested policy reduces specified interviewer-added informational contamination mechanisms. Any experiment on actual false-memory formation belongs to a separately reviewed human-subject protocol with controlled ground truth and debriefing, not to sensitive testimony capture.

## Claim boundary

After Experiment A only, the implementation can support mechanical claims about preservation-before-interpretation, later exact-label emergence without source rewriting, non-collapse, and deterministic guard behaviour.

After completed and adjudicated Experiment B, the paper can support narrow statements about the tested model + policy + researcher-authored scenarios, for example that one policy produced fewer branch-closing interventions or fewer specified contamination opportunities while retaining facilitation. It still cannot establish effects on human memory, participant trust, cultural validity, trauma-informed practice or field effectiveness.
