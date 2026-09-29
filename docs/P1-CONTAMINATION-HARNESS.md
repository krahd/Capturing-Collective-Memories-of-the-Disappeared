# P1 recursive-contamination harness

## Evidence boundary

The first P1 implementation is intentionally a **Level-0 deterministic qualification harness**.  It tests whether the architecture makes the frozen experimental conditions mechanically different and auditable before any model call is treated as evidence.

It does **not** establish conversational quality, participant effects, false memory, or the probability that a deployed LLM will introduce prior-session material.

## Conditions

- **C0 strict capture isolation:** only current-session participant source is visible during capture.
- **C1 naive cross-session memory:** prior archive text is flattened into capture context; this is an intentionally unsafe comparator.
- **C2 source-bounded retrieval:** only explicitly selected participant-source records may enter context, each retaining source provenance.

## Invariants tested

1. B contains no target in participant-authored input.
2. C0 exposes no A material.
3. C1 exposure is intentionally provenance-deficient at the capture boundary.
4. C2 exposure retains explicit source-session/object provenance.
5. Model mediation never silently enters B's participant-source layer.
6. Exact inputs, condition, model mediation and provenance are emitted as auditable results.

## Next evidence level

Level 1 replaces the deterministic leak probe with fixed and fully logged model calls.  The target-equivalence and leadingness rubric must be frozen before those runs.  Level-0 counts must not be repurposed as LLM performance results.
