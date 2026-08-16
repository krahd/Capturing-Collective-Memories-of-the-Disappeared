# RTCA B2 TTFT replication summary

This is a new streaming replication of the frozen B2 protocol. It does not retrofit TTFT into the original B2 run.

**TTFT definition:** request dispatch to the first non-empty streamed model content chunk. Role-only/empty chunks are ignored.

**Admission boundary:** the current guard validates the completed JSON candidate. Model TTFT therefore is not participant-visible response onset; `admission_ready` remains the earliest safe delivery time in this architecture.

| Model | n | Fallback | First-attempt TTFT med/p90 | Accepted-candidate TTFT med/p90 | Accepted first token from decision start med/p90 | Admission-ready med/p90 |
|---|---:|---:|---:|---:|---:|---:|
| qwen3-30b-a3b-primary | 25 | 1/25 | 164.1/346.5 ms | 357.7/379.5 ms | 1549.0/1734.1 ms | 1755.1/1937.9 ms |
| qwen3-4b-scale-control | 25 | 6/25 | 205.4/476.0 ms | 256.5/331.7 ms | 883.7/1032.8 ms | 1365.2/2447.3 ms |
| mistral-small-3-2-cross-family | 25 | 4/25 | 251.9/613.1 ms | 617.4/677.8 ms | 2554.6/4157.0 ms | 4084.4/6007.6 ms |
