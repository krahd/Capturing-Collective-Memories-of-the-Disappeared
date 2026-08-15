# Deferred-significance experiment result

**Created:** 2026-08-15T03:41:14.721232+00:00
**Evidence level:** 0 (mechanical / researcher-authored)

Mechanical and researcher-authored evidence only. This run verifies implemented storage/representation/guard properties and the benchmark harness; it does not measure a language model's interviewing quality, human recollection, participant experience, or historical truth.

## Summary

- total checks: 16/16 passed
- convergence: 5/5 passed
- non-collapse: 3/3 passed
- controller guard probes: 8/8 passed

## Cross-session convergence

| Case | Pass | Target conversation counts | Source unchanged |
|---|---:|---|---:|
| nickname-tito | yes | [1, 2, 3] | yes |
| nickname-flaco | yes | [1, 2, 3] | yes |
| place-bar | yes | [1, 2, 3] | yes |
| object-radio | yes | [1, 2, 3] | yes |
| theme-domingos | yes | [1, 2, 3] | yes |

## Non-collapse checks

| Case | Pass |
|---|---:|
| contradictory-dates | yes |
| unlocated-time | yes |
| uncertainty-remains-mark | yes |

## Controller guard probes

| Case | Expected | Observed | Pass | Delivered |
|---|---|---|---:|---|
| packed-question | fallback | fallback | yes | Contame. |
| unsupported-specificity | fallback | fallback | yes | Contame. |
| generic-acknowledgement | fallback | fallback | yes | Contame. |
| grounded-acknowledgement | accepted | accepted | yes | Mencionás a Tito y que venía por casa. |
| minimal-floor-yield | accepted | accepted | yes | Contame. |
| single-grounded-probe | accepted | accepted | yes | ¿Quién era Tito? |
| uncertainty-hardening | fallback | fallback | yes | Contame. |
| repetitive-backchannel | fallback | fallback | yes | Contame. |

## Interpretation

A passing convergence case means the participant recollection exists before any derived target exists, later sessions can make an exact-label relation visible across conversations, and the original source text remains byte-for-byte unchanged. A passing non-collapse case means the tested ambiguity or contradiction remains represented rather than being silently normalised away. A passing guard probe means the deterministic controller accepted or rejected a researcher-authored candidate intervention as specified.

These checks do not establish that the model will choose the desired move. That is a Level 1 model experiment and must be run against a configured model using the companion protocol.
