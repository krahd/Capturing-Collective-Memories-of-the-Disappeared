# RTCA B2 TTFT replication summary

This is a new streaming replication of the frozen B2 protocol. It does not retrofit TTFT into the original B2 run.

**TTFT definition:** request dispatch to the first non-empty streamed model content chunk. Role-only/empty chunks are ignored.

**Admission boundary:** the current guard validates the completed JSON candidate. Model TTFT therefore is not participant-visible response onset; `admission_ready` remains the earliest safe delivery time in this architecture.

| Model | n | Fallback | First-attempt TTFT med/p90 | Accepted-candidate TTFT med/p90 | Accepted first token from decision start med/p90 | Admission-ready med/p90 |
|---|---:|---:|---:|---:|---:|---:|
| qwen3-30b-a3b-primary | 25 | 0/25 | 166.3/352.4 ms | 363.1/375.1 ms | 1559.5/1780.9 ms | 1771.4/1988.3 ms |
| qwen3-4b-scale-control | 25 | 4/25 | 162.2/243.6 ms | 237.4/247.0 ms | 800.5/937.5 ms | 1219.2/1948.0 ms |
| mistral-small-3-2-cross-family | 25 | 2/25 | 252.8/616.7 ms | 622.8/647.9 ms | 2565.0/4844.7 ms | 4066.6/6486.1 ms |
