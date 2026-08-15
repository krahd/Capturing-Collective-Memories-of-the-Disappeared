# RTCA multi-model automatic screening

This is a conservative automatic screen of researcher-authored model outputs. It is not final adjudication and does not measure human memory.

| Model | Role | Policy | Valid n | Preserve | Redirection | Over-specification | Packed | Floor closure | Generic ack | Hardened uncertainty |
|---|---|---|---:|---:|---:|---:|---:|---:|---:|---:|
| qwen3-30b-a3b-primary | primary | immediate-information | 25 | 14/25 | 0 | 2 | 11 | 0 | 0 | 0 |
| qwen3-30b-a3b-primary | primary | adaptive-semi-structured | 25 | 8/25 | 0 | 5 | 16 | 0 | 0 | 0 |
| qwen3-30b-a3b-primary | primary | deferred-significance | 25 | 25/25 | 0 | 0 | 0 | 0 | 0 | 0 |
| qwen3-4b-scale-control | scale-control | immediate-information | 25 | 4/25 | 0 | 4 | 19 | 0 | 0 | 1 |
| qwen3-4b-scale-control | scale-control | adaptive-semi-structured | 25 | 7/25 | 0 | 14 | 8 | 0 | 0 | 3 |
| qwen3-4b-scale-control | scale-control | deferred-significance | 25 | 23/25 | 0 | 2 | 0 | 0 | 0 | 0 |
| mistral-small-3-2-cross-family | cross-family-control | immediate-information | 25 | 11/25 | 4 | 0 | 10 | 0 | 0 | 2 |
| mistral-small-3-2-cross-family | cross-family-control | adaptive-semi-structured | 25 | 22/25 | 0 | 0 | 3 | 0 | 0 | 0 |
| mistral-small-3-2-cross-family | cross-family-control | deferred-significance | 25 | 23/25 | 0 | 2 | 0 | 0 | 1 | 0 |

## Across-model policy totals

| Policy | Valid n | Preserve | Rate |
|---|---:|---:|---:|
| immediate-information | 75 | 29 | 0.3867 |
| adaptive-semi-structured | 75 | 37 | 0.4933 |
| deferred-significance | 75 | 71 | 0.9467 |
