from __future__ import annotations

import json
from pathlib import Path
import sys

ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from voice import VoiceService


def main() -> int:
    service = VoiceService()
    config = service.config()
    print(json.dumps(config, ensure_ascii=False, indent=2))
    if config["asr_configured"] and config["tts_configured"]:
        print("\nVoice path ready: Whisper input and Piper output are configured.")
        return 0
    print("\nVoice path incomplete. Set the missing values shown above; see docs/VOICE.md.")
    return 1


if __name__ == "__main__":
    raise SystemExit(main())
