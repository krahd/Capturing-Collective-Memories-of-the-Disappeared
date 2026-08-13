"""Drive the whole spoken turn against a running application and time it.

The browser test — a person speaking into a microphone for ten or fifteen turns —
is the only thing that establishes the voice path works, and this does not
replace it. What it does replace is the guessing that happens before it: whether
the resident recogniser is really being used, whether a full turn survives real
audio rather than a mocked transport, and where the seconds actually go.

Participant audio is produced by the project's own Piper voice, so this exercises
ffmpeg conversion, resident Whisper, routing, interviewing and synthesis with
real bytes at every stage. It is synthetic speech, not a person hesitating over a
name, and the transcript it produces will be cleaner than a real one.

    python scripts/check_voice_loop.py --turns 3

Requires the application to be running (`bash start.sh`).
"""

from __future__ import annotations

import argparse
import json
from pathlib import Path
import statistics
import sys
import time

import httpx

ROOT = Path(__file__).resolve().parent.parent

# Ordinary recollections rather than test strings: routing, interviewing and
# extraction all behave differently on material that is actually in scope.
PARTICIPANT_TURNS = [
    "Mi tío Julio trabajaba en el frigorífico del Cerro y una noche no volvió a casa.",
    "Mi vieja guardó las cartas en una caja de zapatos y ahí quedaron muchos años.",
    "No me acuerdo si fue en el setenta y siete o en el setenta y ocho.",
    "En el liceo nadie hablaba del tema, era como si esa gente no hubiera existido.",
    "Nos juntábamos los domingos en la casa de la calle Grecia, éramos como quince.",
]


def run(base_url: str, turns: int, vad_wait_ms: int) -> dict:
    client = httpx.Client(base_url=base_url, timeout=300)
    config = client.get("/api/config").json()
    voice = config.get("voice", {})
    if not voice.get("asr_configured") or not voice.get("tts_configured"):
        raise SystemExit(f"Voz no configurada: {voice.get('missing')}")

    session = client.post("/api/sessions", json={}).json()
    traces = []
    for index in range(turns):
        text = PARTICIPANT_TURNS[index % len(PARTICIPANT_TURNS)]

        # Participant audio, produced the same way the reply will be.
        spoken = client.post("/api/voice/speak", json={"text": text})
        spoken.raise_for_status()
        audio = spoken.content

        transcribe_started = time.perf_counter()
        heard = client.post(
            f"/api/sessions/{session['id']}/voice/transcribe",
            content=audio,
            headers={"Content-Type": "audio/wav", "X-VAD-Wait-Ms": str(vad_wait_ms)},
        )
        heard.raise_for_status()
        heard_payload = heard.json()
        transcribe_ms = round((time.perf_counter() - transcribe_started) * 1000)

        turn_started = time.perf_counter()
        turn = client.post(
            f"/api/sessions/{session['id']}/turns",
            json={"text": heard_payload["text"], "audio_id": heard_payload["audio_id"]},
        )
        turn.raise_for_status()
        turn_payload = turn.json()
        turn_ms = round((time.perf_counter() - turn_started) * 1000)

        reply = turn_payload["assistant_turn"]["text"]
        synth_started = time.perf_counter()
        synthesized = client.post("/api/voice/speak", json={"text": reply})
        synthesized.raise_for_status()
        synth_ms = round((time.perf_counter() - synth_started) * 1000)

        trace = {
            "turn": index + 1,
            "said": text,
            "heard": heard_payload["text"],
            "resident_asr": heard_payload["asr"].get("resident", False),
            "intent": turn_payload["intent"],
            "move": turn_payload["move"],
            "reply": reply,
            **heard_payload.get("timings_ms", {}),
            "transcribe_round_trip_ms": transcribe_ms,
            **turn_payload.get("timings_ms", {}),
            "turn_round_trip_ms": turn_ms,
            "tts_synthesis_ms": int(synthesized.headers.get("X-TTS-Synthesis-Ms", 0)),
            "tts_round_trip_ms": synth_ms,
        }
        # What a participant would experience: their own silence, plus everything
        # between it and the first sound of the reply.
        trace["perceived_reply_ms"] = (
            vad_wait_ms + transcribe_ms + turn_ms + synth_ms
        )
        traces.append(trace)
        client.post("/api/latency", json=trace)

    field = client.get("/api/memory-field").json()
    client.close()
    return {"session_id": session["id"], "traces": traces, "field": field, "config": config}


def report(summary: dict) -> None:
    traces = summary["traces"]
    print(f"sesión: {summary['session_id']}")
    print(f"ASR: {summary['config']['voice']['asr_mode']}  TTS: {summary['config']['voice']['tts_mode']}")
    print()
    for trace in traces:
        print(f"— turno {trace['turn']}  [{trace['intent']} / {trace['move']}]  residente={trace['resident_asr']}")
        print(f"  dijo:  {trace['said']}")
        print(f"  oyó:   {trace['heard']}")
        print(f"  responde: {trace['reply']}")
        print(
            f"  vad {trace.get('vad_wait_ms', 0)} + conversión {trace.get('audio_conversion_ms', 0)}"
            f" + asr {trace.get('asr_ms', 0)} + ruteo {trace.get('classify_ms', 0)}"
            f" ({trace.get('classification_source', '?')}) + entrevista {trace.get('interview_ms', 0)}"
            f" + tts {trace['tts_synthesis_ms']} = {trace['perceived_reply_ms']} ms"
        )
        print()

    print("medianas (ms):")
    for stage in (
        "audio_conversion_ms",
        "asr_ms",
        "classify_ms",
        "interview_ms",
        "tts_synthesis_ms",
        "perceived_reply_ms",
    ):
        values = [t[stage] for t in traces if isinstance(t.get(stage), (int, float))]
        if values:
            print(f"  {stage:24} {round(statistics.median(values)):>6}")

    if not all(trace["resident_asr"] for trace in traces):
        print("\nAVISO: al menos un turno usó whisper-cli en vez del servidor residente.")

    field = summary["field"]
    print(f"\ncampo de memoria: {len(field.get('nodes', []))} nodos, {len(field.get('edges', []))} vínculos")


def main() -> int:
    parser = argparse.ArgumentParser(description=__doc__)
    parser.add_argument("--base-url", default="http://127.0.0.1:8765")
    parser.add_argument("--turns", type=int, default=3)
    parser.add_argument(
        "--vad-wait-ms",
        type=int,
        default=1700,
        help="silencio de fin de turno que el navegador espera realmente",
    )
    parser.add_argument("--json", type=Path)
    args = parser.parse_args()

    summary = run(args.base_url, max(1, args.turns), args.vad_wait_ms)
    report(summary)
    if args.json:
        args.json.parent.mkdir(parents=True, exist_ok=True)
        args.json.write_text(json.dumps(summary, ensure_ascii=False, indent=2), encoding="utf-8")
        print(f"escrito: {args.json}")
    return 0 if all(trace["resident_asr"] for trace in summary["traces"]) else 1


if __name__ == "__main__":
    sys.exit(main())
