# Local half-duplex voice

The optional voice path is deliberately simple:

```text
browser microphone → end-of-turn silence → ffmpeg → whisper.cpp (Spanish)
→ constrained conversation controller → Piper es_AR → browser speakers
```

The microphone is stopped before transcription begins and remains off while the
reply is synthesized and played. There is no wake word, barge-in, simultaneous
listening, or end-to-end speech model.

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
WHISPER_MODEL=/absolute/path/to/ggml-large-v3-turbo.bin
WHISPER_LANGUAGE=es
```

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

The service uses Piper's Python API when installed, keeping the voice model in
memory after its first use. It can fall back to a standalone `piper` executable
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
**Hablar**, speak naturally, and leave roughly 1.25 seconds of silence.

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
