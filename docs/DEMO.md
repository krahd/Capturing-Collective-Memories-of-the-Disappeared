# Tomorrow demo runbook

This is a one-laptop research/design demonstration using only synthetic or non-sensitive colleague material. The conversation is not scripted. The prototype must remain useful when a contribution does not converge with anything already in the corpus.

The proposition to land, in this order:

> A contribution is preserved first, interpreted provisionally, and may acquire significance only after entering relation with other contributions.

The graph is not “collective memory,” recurrence is not truth, and the meeting is not a participant study.

## Before colleagues arrive

From the repository:

```bash
ollama serve
bash start.sh --voice-doctor
python scripts/validate_demo_corpus.py
pytest -q
bash start.sh
```

Open `http://127.0.0.1:8765`. Confirm:

- the page opens in **Contribuir**, with no graph visible;
- the status says **voz local lista**;
- **Empezar por voz**, **Pausar** and **Terminar contribución** are visible;
- **Explorar el corpus** opens a field containing ten seed conversations and about 68 nodes;
- `Tito` says **aparece en 3 conversaciones**;
- returning to **Contribuir** releases the microphone if it was active;
- the complete layout fits the actual meeting resolution.

Do a disposable preflight to remove first-inference cost:

```bash
python scripts/check_voice_loop.py --turns 2 --vad-wait-ms 2200
```

The diagnostic creates and deletes its own temporary run. Do not leave a rehearsal contribution in the meeting sandbox.

## Demonstration sequence

### 1. Contribute

Open **Contribuir** and read the short ground rule aloud: temporary data, no sensitive information, and the ability to forget, correct, skip, pause or stop.

Invite a colleague to speak normally. Do not prescribe a sentence or steer them toward a seed name. The opening is deliberately broad: *«Podés empezar por donde quieras. ¿Qué te gustaría contar?»*

Useful things to notice without interrupting the exchange:

- the system can yield with `Ajá.`, `Contame.` or `Cuando quieras.` instead of asking a question every turn;
- a correction remains a new source turn rather than silently replacing the earlier words;
- a privacy/storage question receives the fixed application-owned answer, not invented model policy;
- **Pausar**, **Reanudar** and **Terminar contribución** are participant-owned controls and do not fabricate spoken transcript turns.

### 2. Explore deliberately

Switch to **Explorar el corpus**. This is explicitly the researcher view, not what the participant sees while contributing.

The first reveal follows stored order:

1. **Contribución preservada** — the conversation and recollection exist before interpretation succeeds;
2. **Interpretación provisional incorporada** — only actual extracted items appear;
3. **Posible coincidencia entre conversaciones** — only if the live contribution truly reaches a label found elsewhere.

A live contribution need not converge. If it does not, say so: preservation is not conditional on recurrence. Then open the frozen `Tito` node to show the deferred-significance example across three independent synthetic sources:

- somebody called Tito sometimes appeared at a house;
- Tito lived around La Teja;
- Julio may have used the name Tito.

The system has not established that these mentions are one historical person. It exposes a possible relation and retains each exact source.

### 3. Inspect chronology and provenance

Open **Cronología**. Show that contradictory years remain separate and source-linked rather than being averaged or adjudicated.

Open a node and then **Registro**. Point out the separation between participant words, ASR, application actions and model-derived interpretation. Detailed model residency and settings belong here, while capture mode shows only **voz local lista**.

### 4. Let colleagues play

Use **Nueva contribución** for each colleague. Every session remains in the same temporary meeting run, so the researcher view can show the seed corpus plus this run while excluding old experimental sessions.

Keep the material ordinary and non-sensitive. The most informative test is a real, unscripted exchange with uncertainty, pauses, a correction or a topic change—not successful recitation of a prepared fragment.

### 5. Clear visibly

Press **Borrar datos temporales** before closing. This removes only the current meeting run and its temporary audio. It does not touch the frozen seed corpus or persistent research sessions.

## Fallbacks

- If microphone capture fails, open **Escribir en vez de hablar** and continue the same unscripted contribution by text.
- If the model fails, switch to **Explorar el corpus**. The frozen 10-conversation field, `Tito`, chronology and provenance remain available without rebuilding.
- **Ejemplo grabado** is a labelled, idempotent researcher-authored transcript. It is excluded from the aggregate demo corpus.
- If the app is restarted, all ephemeral meeting runs disappear by design.

## What is verified

As of 13 August 2026:

- 109 deterministic tests pass;
- the frozen corpus validator reports 10 conversations, 68 nodes, 74 relations, Tito in 3 conversations and one open contradictory chronology;
- the 49-case adversarial router has no critical failures on the configured 30B model;
- a five-turn synthetic full voice loop used resident ASR and TTS on every turn, with 4.48 s median perceived response including the 2.2 s silence window;
- real cleanup was reproduced after background extraction: the deleted session returned 404, no persistent JSON existed, and no run identifier remained under `data/` or `demo/`.

Still manual: one 10–15-turn human browser conversation with a deliberate 1.8-second mid-sentence hesitation, and the final visual smoke test at meeting resolution.

## What not to claim

Do not claim:

- cultural validity, safety, usability or successful memory capture;
- that recurrence means importance, credibility, confirmation or truth;
- that same-label nodes establish historical identity;
- that the current half-duplex browser loop is the production speech architecture;
- that consent, relational privacy, revocation, access or governance are solved;
- that this colleague demonstration is participant evidence.
