# Demo runbook

A short sequence for showing the prototype. Everything below runs on this
machine with no network.

## Before the meeting

```bash
ollama serve                                   # if not already running
ollama run qwen3:30b-a3b-instruct-2507-q4_K_M ""   # warms the model into memory
bash start.sh                                  # or the VS Code "Prototype: Run" task
```

Open `http://127.0.0.1:8765`. Check the badge at the top right reads
`qwen3:30b-a3b-instruct-2507-q4_K_M · local` in green. That badge is the claim
that nothing leaves the machine; it is worth pointing at.

The first reply after starting is slow while the model loads. Warm it first.

## Sequence

**1. The conversation.** New conversation, then talk to it in Uruguayan Spanish.
Material that exercises the design: an approximate date, something known only
through someone else, a correction a few turns later, a refusal followed by an
offered alternative.

Do not claim the conversational quality is validated. It is not — see
`docs/TEST-REPORT.md`. If it produces a bad turn, that is usable: the failures
are the current research output.

**2. Capture.** Tick a few participant turns, then **Extraer provisionalmente con
el modelo**. Takes a few seconds. The items appear grouped by kind, each with an
amber `modelo` badge naming the exact model.

Point out the contrast: add one yourself in **Material derivado** and it carries a
blue `investigador` badge. Machine interpretation and human interpretation are
never stored or shown as the same thing.

**3. Provenance.** Click any item's header — the exact turns it came from light up
in the transcript. Click the `N interpretaciones` chip on a turn to isolate what
cites it. Nothing derived floats free of the words that produced it.

**4. Withdrawal.** Find an item the model got wrong — over-reach is common — and
press **Retirar**, giving a reason. It stays on screen, struck through, with the
reason attached. It is marked, not erased.

Worth saying explicitly: **Eliminar** exists and is genuinely destructive; it also
redacts the quotations the session record itself kept, and records that the
redaction happened. The system does not pretend deletion is impossible, and it
does not pretend it is free.

**5. Audit.** The **Auditoría** tab: counts, then every action attributed to
`participante`, `investigador`, `modelo` or `sistema`, with the model's exact
sampling settings on each machine-made entry.

**6. Export.** **Markdown** — the whole session, transcript, attributions,
withdrawals and record, readable without this application.

## If the model fails mid-meeting

Press **Sesión de ejemplo**. It loads a researcher-authored transcript with
material of both origins, an edit, and a withdrawal already in place, so steps
3–6 work unchanged. It is labelled on screen as a recorded transcript and refuses
new turns. Say that it is authored, not participant testimony.

## Useful URLs

- `?session=<id>` opens a specific session
- `?tab=audit` opens straight to the audit panel

## What not to claim

Naturalness, cultural validity, safety, or successful memory capture. None of
those have evidence yet. What does have evidence: the transcript is preserved
exactly, interpretation is attributable and reversible, and the whole thing runs
locally.
