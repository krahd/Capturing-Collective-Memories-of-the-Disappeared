# Deferred-significance experiment result — 14 August 2026

**Run:** GitHub Actions `31856109446`  
**Source commit:** `06eac0f4e74f745684c6f7d24c648b78f580d5ba`  
**Generated:** 2026-08-15T01:17:59.453026+00:00 (14 August local research date)  
**Evidence level:** 0 (mechanical / researcher-authored)  
**Artifact:** `9239068474`, ZIP SHA-256 `5216bd0754c2625bebaa11c2cba7fa0470755120ae4a7a9f66f9f7cd042f2a4e`

Mechanical and researcher-authored evidence only. This run verifies implemented storage/representation/guard properties and the benchmark harness; it does not measure a language model's interviewing quality, human recollection, participant experience, or historical truth.

## Summary

- total checks: **16/16 passed**
- cross-session convergence: **5/5 passed**
- non-collapse: **3/3 passed**
- controller guard probes: **8/8 passed**
- benchmark-specific pytest checks: **2/2 passed**
- repository main CI at the same source commit: **passed** (`31856109506`)

## Cross-session convergence

| Case | Target | Conversation trajectory | Recollection before interpretation | Target before interpretation | Source unchanged |
|---|---|---|---:|---:|---:|
| nickname-tito | `person:tito` | `[1, 2, 3]` | yes | no | yes |
| nickname-flaco | `person:flaco` | `[1, 2, 3]` | yes | no | yes |
| place-bar | `place:bar de la esquina` | `[1, 2, 3]` | yes | no | yes |
| object-radio | `entity:radio spika` | `[1, 2, 3]` | yes | no | yes |
| theme-domingos | `theme:reuniones de los domingos` | `[1, 2, 3]` | yes | no | yes |

In every case, the source recollection existed before a derived target node; later sessions made the exact-normalised target shared across conversations; the original session-A text remained byte-for-byte unchanged.

## Non-collapse checks

| Case | Expected | Observed | Result |
|---|---|---|---:|
| contradictory-dates | `el 77`, `el 78` remain separate | both retained | pass |
| unlocated-time | `después` remains undated | retained as undated | pass |
| uncertainty-remains-mark | uncertainty retained | `uncertainty` mark retained | pass |

## Controller guard probes

| Case | Required behaviour | Observed | Result |
|---|---|---|---:|
| packed-question | reject / floor-yield | `Contame.` | pass |
| unsupported-specificity | reject / floor-yield | `Contame.` | pass |
| generic-acknowledgement | reject / floor-yield | `Contame.` | pass |
| grounded-acknowledgement | accept | `Mencionás a Tito y que venía por casa.` | pass |
| minimal-floor-yield | accept | `Contame.` | pass |
| single-grounded-probe | accept | `¿Quién era Tito?` | pass |
| uncertainty-hardening | reject / floor-yield | `Contame.` | pass |
| repetitive-backchannel | reject / floor-yield | `Contame.` | pass |

## Interpretation

The run provides mechanical evidence for four implementation claims relevant to *Conditions of Recollection*:

1. participant recollections are represented before interpretation;
2. later conversations can make a previously local exact-label relation visible without modifying the earlier source;
3. the tested contradiction, temporal indeterminacy and uncertainty survive representation;
4. the deterministic controller rejects the tested packed, unsupported, generic, certainty-hardening and repetitive interventions while permitting a grounded acknowledgement, a single grounded probe and a minimal invitation to continue.

This does **not** establish that the language model reliably chooses those moves, nor that these policies improve human recollection. The Level-1 live-model policy comparison specified in `evaluation/DEFERRED-SIGNIFICANCE-EXPERIMENT.md` remains a separate experiment.
