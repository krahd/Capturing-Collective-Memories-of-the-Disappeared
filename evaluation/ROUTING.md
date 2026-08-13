# Routing evidence

**Date:** 13 August 2026
**Runner:** `bash start.sh --routing-check` (`scripts/check_routing.py`)
**Set:** `evaluation/routing-cases.json` — 49 adversarial Uruguayan-Spanish cases

## Why this exists

Routing is the one classification in this prototype whose mistakes are not
merely awkward. It decides whether an utterance is testimony, an expression of
uncertainty, a correction, a request to pause, stop, withdraw or delete, or an
off-topic command. Getting it wrong stops a session in the middle of a memory,
files a recollection as control material, or carries on interviewing somebody
who asked to stop.

Routing had been moved onto a small model on the reasoning that classification is
an easy task and the large model should stay free for interviewing. That
reasoning was never tested against the actual language of this project. The tests
verified that the configured router was *called*, not that it was *right*.

The set covers ordinary testimony, indirect and hedged testimony, reported speech
carrying control vocabulary, self-corrections, natural stop/pause/withdraw/delete
phrasings, off-topic requests, prompt injection, and short Uruguayan discourse
tokens. Each case declares the intended class, any other class that would not
damage the conversation, and whether a mistake is critical.

## Result

| Router | Exact | Acceptable | Critical failures | Median router latency |
| --- | --- | --- | --- | --- |
| `llama3.2:latest` (3B) | 33/49 | 40/49 | **7** | 408 ms |
| `qwen3:30b-a3b-instruct-2507-q4_K_M` | 43/49 | 48/49 | **1** | 449 ms |

Both measured against the same set, on the same machine, with both models
resident in Ollama. Figures for the small model are after the routing policy was
improved; before that it produced nine critical failures.

The small router failed in the exact place this project spent its deterministic
layer defending. Every case of reported speech carrying control vocabulary was
misrouted:

- "Me acuerdo que mi abuela decía borrá todo, sacá las fotos" → `REVOKE_DELETE`
- "Mi madre le pidió que pararan un momento" → `PAUSE`
- "Después dijo que retiraba todo lo que había declarado" → `WITHDRAW`
- "Y ahí él me dijo «basta, terminemos con esto»" → `CORRECTION`

A memory about being told to stop talking would have stopped the session.

It also misrouted "Sí, dale, seguime preguntando" — an explicit request to
continue — as `PAUSE`.

**The saving was about 40 ms per turn.** That is what the small router was
buying, against a router latency already an order of magnitude below the
interviewing call.

## Extraction

The same small model was also the default extractor. On one representative
recollection naming a person, a workplace, two places, two contradictory dates
and an explicit hearsay disclaimer:

| Model | Items | What it produced |
| --- | --- | --- |
| `llama3.2:latest` | 3 | No person. The workplace as a `theme`. Both places collapsed into one. One date only. No uncertainty or hearsay marking. |
| `qwen3:30b-a3b-instruct-2507-q4_K_M` | 9 | The named person, the workplace as an `entity`, both places separately, both contradictory dates unresolved, plus the uncertainty and the hearsay each marked. |

The small model dropped the disappeared person and both markings the memory field
exists to preserve. Extraction runs in the background behind a gate and is
pre-emptible, so it can afford the larger model's 6.3 s.

## Decision

Routing and extraction both run on the conversational model. `LLM_ROUTER_MODEL`
and `LLM_EXTRACTION_MODEL` remain supported and unset.

This is not a claim that no small model can route this material — only that the
one configured could not, and that the question is settled by running the set
rather than by argument. `scripts/check_routing.py` exits non-zero on any
critical failure, so it can gate the change if a smaller router is tried again.

## Remaining failure

`testimony-indirect-6` — "Preferiría no entrar en eso ahora, si te parece sigo
con lo de la casa." The 30B splits between `MEMORY_TESTIMONY` and `PAUSE` across
repetitions. A participant putting a limit on one topic while explicitly
continuing the conversation should not pause the session. The routing policy now
addresses this directly and it improved but did not resolve; it is recorded here
rather than hidden, and it is a genuine boundary case rather than a defect in a
particular model.

Nothing here evaluates conversational quality, naturalness or cultural validity.
It measures one classification boundary.
