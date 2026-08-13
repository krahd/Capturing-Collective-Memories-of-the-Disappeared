# Local half-duplex voice

The optional voice path is deliberately simple:

```text
browser microphone → end-of-turn silence → ffmpeg → resident whisper.cpp (Spanish)
→ constrained conversation controller → Piper es_AR → browser speakers
→ microphone again
```

The same microphone stream and audio analyser remain allocated across turns,
but the audio track is disabled before transcription and while the reply is
synthesized and played. There is no wake word, barge-in, simultaneous listening,
or end-to-end speech model.

## Continuous half-duplex

The loop re-arms by itself. **Hablar** starts an exchange and **Terminar** ends
it; between turns nothing is pressed. Pressing a button for every single
utterance is what makes a voice interface feel like a form rather than a
conversation, and re-arming gives most of the experiential benefit of barge-in
at none of its risk.

The loop also ends on its own if a re-armed microphone hears nothing for 20
seconds, so it never sits open indefinitely.

Barge-in — interrupting the system mid-sentence — is the next increment and is
deliberately not built. It should not be attempted until the ordinary path has
been shown to be reliable in a real spoken conversation.

## End of turn

A turn ends after **1.7 seconds** of silence.

That number is a claim about this conversation, not a technical default. A memory
conversation is full of hesitation — people stop mid-sentence while reaching for
a name, a year, a street — and a threshold tuned for command-and-control speech
cuts them off exactly where the material is hardest to retrieve. It remains demo
turn detection rather than archival VAD; it is simply tuned for reflective speech
instead of instructions.

## 1. Install speech recognition

On Apple Silicon with Homebrew:

```bash
brew install ffmpeg whisper-cpp
```

Whisper.cpp does not install a model automatically. Download a multilingual
GGML model from the official `ggerganov/whisper.cpp` collection. For the demo,
`ggml-large-v3-turbo.bin` is the intended target. Configure its absolute path:

```bash
WHISPER_CLI=/opt/homebrew/bin/whisper-cli
WHISPER_SERVER=/opt/homebrew/bin/whisper-server
WHISPER_MODEL=/absolute/path/to/ggml-large-v3-turbo.bin
WHISPER_LANGUAGE=es
```

At application startup, `whisper-server` loads that model once and stays
resident. Each turn is posted to its `/inference` endpoint. `whisper-cli` remains
configured as a fallback if the resident process cannot start or disappears.

`WHISPER_SERVER_URL` only changes the address, and a server already answering
there is reused rather than duplicated — so setting it does not disable the
resident server. To keep the application from ever launching one, because
something else supervises it, set `WHISPER_SERVER_EXTERNAL=1` explicitly.

Startup confirms the address by asking it to transcribe a fraction of a second of
silence. Something else holding the port answers that wrongly and is refused,
instead of being adopted as the recogniser and failing on the first real turn.

Check which path is live before trusting a demo:

```bash
curl -s http://127.0.0.1:8765/api/config | python3 -m json.tool | grep -A2 asr_mode
```

`asr_mode: resident` is the fast path. `cli_fallback` still transcribes, but it
reloads the whole model for every turn and gives up the main reason this path
exists.

Official model files: <https://huggingface.co/ggerganov/whisper.cpp/tree/main>

## 2. Install speech synthesis

Install the maintained Open Home Foundation Piper package inside the project
environment (or run the VS Code task **Prototype: Install Piper**):

```bash
. .venv/bin/activate
pip install -r requirements-voice.txt
mkdir -p models/piper
python -m piper.download_voices es_AR-daniela-high --data-dir models/piper
```

The current Argentine Spanish voice is `es_AR-daniela-high`. Point
`PIPER_MODEL` at the downloaded `.onnx` file using an absolute path:

```bash
PIPER_MODEL=/absolute/path/to/models/piper/es_AR-daniela-high.onnx
```

The service uses Piper's Python API when installed. The voice is loaded at
application startup by synthesizing one discarded sentence, so the first spoken
reply does not pay for the load; `tts_mode` in `/api/config` reports `resident`
once that has happened. It can fall back to a standalone `piper` executable
configured with `PIPER_CLI`.

Official voice list: <https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md>

## 3. Configure and check

Put the variables in the repository's ignored `.env`; `.env.example` contains
the complete template. Then run the VS Code task **Prototype: Voice Doctor**, or:

```bash
bash start.sh --voice-doctor
```

Start the normal **Prototype: Run** task. When both layers are ready, the
conversation composer shows `voz local · es · entrada y salida`. Press
**Hablar** once and then just talk: pause for a couple of seconds when you have
finished a turn, listen to the reply, and keep going. Press **Terminar** to close
the exchange.

## Where the time goes

Every stage is measured. The browser posts the assembled trace of each spoken
turn to `/api/latency`, which keeps the last 64 and reports medians:

```bash
curl -s http://127.0.0.1:8765/api/latency | python3 -m json.tool
```

Ten consecutive turns on the target machine, medians in milliseconds:

| Stage | ms |
| --- | --- |
| `vad_wait_ms` — silence before the turn is taken as finished | 1700 |
| `audio_conversion_ms` — ffmpeg to 16 kHz mono | 54 |
| `asr_ms` — resident whisper.cpp | 466 |
| `classify_ms` — routing | 662 |
| `interview_ms` — conversational move | 1145 |
| `tts_synthesis_ms` — Piper | 334 |
| **`perceived_reply_ms`** — silence to first audible word | **4581** |

`perceived_reply_ms` is measured in the browser, because the browser holds the
only clock spanning the whole thing: the participant falls silent there and hears
the reply there. Numbers assembled from server stages alone would omit exactly
the parts nobody measures and everybody notices.

The largest single item is the deliberate one. The next largest is the
conversational model, which is the thing being demonstrated.

`scripts/check_voice_loop.py` drives the same path against a running application
using the project's own Piper voice as the participant, which is how these
figures were produced. It exercises real audio through real ffmpeg, real Whisper
and real synthesis — but it is synthetic speech, and a person hesitating over a
name will not transcribe as cleanly.

## Representation and limits

- Original browser audio is stored under ignored `data/audio/<session>/`.
- The Whisper transcript is a separate machine-derived record with model and
  language provenance. The participant turn points to both layers.
- Off-topic commands remain in the immutable transcript as
  `non_testimony/control`, but are excluded from interviewer context and
  automatic memory extraction.
- `STOP`, `PAUSE`, `WITHDRAW`, and `REVOKE_DELETE` are application protocol
  operations. A revocation request stops the session but does not pretend that
  this disposable prototype implements a final governance-compliant deletion
  workflow.
- Browser silence detection is a demo turn detector, not archival VAD. Use
  headphones if speaker bleed is a concern, even though the microphone is off
  during playback.
- **The voice path has no automated coverage of the speech itself.** The tests
  verify configuration detection, path resolution and MIME handling; they do not
  exercise Whisper, Piper, browser silence detection, or a complete spoken turn.
  Treat voice as unverified until a real browser conversation of 10–15 turns has
  been held, with ordinary reflective pauses, and record the result in
  `docs/TEST-REPORT.md`.
