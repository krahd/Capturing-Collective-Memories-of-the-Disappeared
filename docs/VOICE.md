# Local half-duplex voice

This document describes the voice path in the disposable prototype. It is not the production speech architecture.

The current optional path is deliberately simple:

```text
browser microphone → end-of-turn silence → ffmpeg → resident whisper.cpp (Spanish)
→ constrained conversation controller → Piper es_AR → browser speakers
→ microphone again
```

The same microphone stream and audio analyser remain allocated across turns, but the audio track is disabled before transcription and while the reply is synthesised and played. There is no wake word, barge-in, simultaneous listening, or end-to-end speech model.

Long-lived voice requirements are in [`FUTURE-ARCHITECTURE.md`](FUTURE-ARCHITECTURE.md) and [`EVALUATION-FRAMEWORK.md`](EVALUATION-FRAMEWORK.md). The current production direction is mobile-first, speech-first and full duplex. Participant interruption should be easy; system interruption should be conservative.

## Continuous half duplex

The loop re-arms by itself. **Hablar** starts an exchange and **Terminar** ends it; between turns nothing is pressed. This removes the repeated push-to-talk burden while retaining a simple implementation for the present test phase.

The loop also ends on its own if a re-armed microphone hears nothing for 20 seconds, so it never sits open indefinitely.

Barge-in is deliberately not built in this prototype. That is a prototype limitation, not a conclusion that half duplex is adequate for the final system. A production full-duplex interface must eventually allow a participant to interrupt immediately, continue after an apparent turn boundary, overlap naturally, and correct the system before it finishes an incorrect intervention.

## End of turn

The current prototype ends a turn after **1.7 seconds** of detected silence.

This is an experimental endpointing heuristic, not an interactional optimum and not an archival definition of a completed recollection. A memory conversation is full of hesitation: people stop mid-sentence while reaching for a name, a year or a street. A threshold tuned for command-and-control speech can cut them off exactly where the material is hardest to retrieve.

The future full-duplex system must separate:

- technical readiness to respond;
- the interactional decision to claim the floor;
- participant-owned silence and continuation.

See [OHA evaluation guidance](https://oralhistory.org/oha-guidelines-for-the-evaluation-of-oral-historians/) and [Kubo et al., SIGDIAL 2026](https://aclanthology.org/2026.sigdial-1.2/) for the methodological and turn-taking background recorded in the project research reviews.

## 1. Install speech recognition

On Apple Silicon with Homebrew:

```bash
brew install ffmpeg whisper-cpp
```

Whisper.cpp does not install a model automatically. Download a multilingual GGML model from the official `ggerganov/whisper.cpp` collection. For the demo, `ggml-large-v3-turbo.bin` is the intended target. Configure its absolute path:

```bash
WHISPER_CLI=/opt/homebrew/bin/whisper-cli
WHISPER_SERVER=/opt/homebrew/bin/whisper-server
WHISPER_MODEL=/absolute/path/to/ggml-large-v3-turbo.bin
WHISPER_LANGUAGE=es
```

At application startup, `whisper-server` loads that model once and stays resident. Each turn is posted to its `/inference` endpoint. `whisper-cli` remains configured as a fallback if the resident process cannot start or disappears.

Do **not** set `WHISPER_SERVER_URL` for the normal app-managed configuration above. Set it only when a Whisper server is already launched and supervised separately; an explicit URL tells the application to reuse that external service rather than launch `WHISPER_SERVER` itself.

Official model files: <https://huggingface.co/ggerganov/whisper.cpp/tree/main>

## 2. Install speech synthesis

Install the maintained Open Home Foundation Piper package inside the project environment (or run the VS Code task **Prototype: Install Piper**):

```bash
. .venv/bin/activate
pip install -r requirements-voice.txt
mkdir -p models/piper
python -m piper.download_voices es_AR-daniela-high --data-dir models/piper
```

The current Argentine Spanish voice is `es_AR-daniela-high`. Point `PIPER_MODEL` at the downloaded `.onnx` file using an absolute path:

```bash
PIPER_MODEL=/absolute/path/to/models/piper/es_AR-daniela-high.onnx
```

The service uses Piper's Python API when installed, keeping the voice model in memory after its first use. It can fall back to a standalone `piper` executable configured with `PIPER_CLI`.

Official voice list: <https://github.com/OHF-Voice/piper1-gpl/blob/main/docs/VOICES.md>

## 3. Configure and check

Put the variables in the repository's ignored `.env`; `.env.example` contains the complete template. Then run the VS Code task **Prototype: Voice Doctor**, or:

```bash
bash start.sh --voice-doctor
```

Start the normal **Prototype: Run** task. When both layers are ready, the conversation composer shows `voz local · es · entrada y salida`. Press **Hablar** once and then talk: pause when you have actually finished a turn, listen to the reply, and keep going. Press **Terminar** to close the exchange.

Verify through `/api/config` and the session record that ASR is actually using the resident path rather than silently falling back to `whisper-cli`; otherwise the main per-turn latency optimisation is not being exercised.

## Source and transcript status

For spoken capture, the original participant audio and the ASR transcript are not equivalent objects.

The current prototype preserves original browser audio under ignored `data/audio/<session>/` and stores the Whisper text as a separate machine-derived transcript with model/language provenance. The participant turn points to both layers.

The long-term source hierarchy is:

```text
participant audio                    source
       ↓
ASR transcript                       machine derivation
       ↓
participant-corrected transcript     participant-authorised derivation
       ↓
research/editorial transcript        research derivation
```

Later forms must not silently overwrite earlier ones. This distinction matters particularly for names, places, nicknames and dates because a single ASR error can propagate into corpus interpretation.

## Current representation and limits

- Off-topic commands remain in the immutable transcript as `non_testimony/control`, but are excluded from interviewer context and automatic memory extraction.
- `STOP`, `PAUSE`, `WITHDRAW`, and `REVOKE_DELETE` are application protocol operations. A revocation request stops the session but does not pretend that this disposable prototype implements a final governance-compliant deletion workflow.
- Browser silence detection is a demo turn detector, not archival VAD.
- The participant cannot interrupt Piper while it speaks. This is a known limitation of the current prototype and conflicts with the production full-duplex requirement.
- The current interface is a desktop/browser research instrument, not a mobile participant-interface specification.

## Verification gate

The voice path has deterministic coverage of configuration/path handling and a mocked resident-Whisper request, but no automated test exercises real Whisper audio recognition, Piper playback, browser silence detection, microphone behaviour and the complete spoken round trip together.

Treat voice as empirically unverified until a real browser conversation of 10–15 turns has been held with ordinary reflective pauses and the result recorded in `docs/TEST-REPORT.md`.

For that run, record at least:

- VAD/endpointing delay;
- ffmpeg conversion;
- ASR latency;
- routing/classification latency;
- interviewer latency;
- TTS synthesis/playback latency if instrumented;
- ASR errors on names, places, nicknames and dates;
- turns cut short by the 1.7-second heuristic;
- cases in which a participant wanted to interrupt system speech but could not.

These measurements diagnose the disposable prototype. They should not be treated as the final full-duplex evaluation protocol; that is defined in [`EVALUATION-FRAMEWORK.md`](EVALUATION-FRAMEWORK.md).
