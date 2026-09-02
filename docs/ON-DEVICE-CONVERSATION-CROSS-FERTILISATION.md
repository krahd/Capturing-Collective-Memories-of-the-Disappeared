# On-device mobile conversation — cross-fertilisation note

**Date:** 1 September 2026  
**Status:** production-direction experiment; no production dependency selected

## Why this exists

A separate private commercial project, URSULA, is beginning a fully on-device mobile conversational proof of concept. The technical problem substantially overlaps with this project's already documented production target: mobile-first, speech-first conversational capture with strong privacy, interruption and offline/intermittent operation.

The overlap is useful, but it must not blur project ownership or create a hidden proprietary dependency in this public research repository.

This document records the shared **technical questions** and a candidate experimental stack using only public references. It does not import URSULA product code, storytelling semantics or commercial project state.

## Shared technical substrate under test

Both systems need some version of:

```text
microphone
   ↓
local voice activity / turn evidence
   ↓
streaming ASR
   ↓
text conversation model
   ↓
experience-specific policy
   ↓
local TTS
   ↓
speaker
```

The production-relevant questions shared by both projects include:

- whether useful Spanish conversation can remain fully on-device on current phones;
- latency from usable end-of-turn evidence to first audible response;
- whether a cascaded system can support participant barge-in without a monolithic full-duplex speech model;
- memory, battery and thermal cost;
- Rioplatense/Uruguayan ASR behaviour;
- local TTS quality and pronunciation;
- model and voice provenance;
- offline operation;
- model/version reproducibility;
- clean separation between generic runtime and project-specific mediation policy.

## Candidate first iPhone proof

### ASR: Moonshine Spanish Streaming

Moonshine Voice currently provides on-device streaming Spanish ASR, including Small Streaming (123M) and Tiny Streaming (34M) models, with native iOS support. The current streaming Spanish models are MIT-licensed.

This is a better first mobile experiment than moving the current desktop `whisper.cpp` configuration unchanged onto the phone: the point of the experiment is to test an architecture designed for streaming mobile use.

Public references:

- https://github.com/moonshine-ai/moonshine
- https://github.com/moonshine-ai/moonshine/blob/main/docs/models/available-models.md
- https://github.com/moonshine-ai/moonshine-swift

Generic Spanish benchmark scores are not sufficient evidence for this project. Evaluation must include Uruguayan/Rioplatense speech, participant pace, names, places, code-switching and historically specific vocabulary.

### Local text model: Apple Foundation Models as first iOS baseline

Apple's Foundation Models framework provides an on-device multilingual language model with Spanish support, multi-turn sessions, structured/guided generation and tool calling on compatible devices.

This makes it a useful first systems baseline because it allows the experiment to isolate whether a fully local conversation loop is viable without first solving open-model deployment.

It must **not** become the sole research path because:

- availability depends on Apple-Intelligence-capable hardware;
- model behaviour changes with OS/model releases;
- context is bounded;
- the exact system model is not a fixed researcher-distributed checkpoint.

Every experiment using it must therefore record device, OS/model environment and prompt/policy version.

Public references:

- https://developer.apple.com/documentation/FoundationModels
- https://developer.apple.com/documentation/foundationmodels/supporting-languages-and-locales-with-foundation-models

### Open-model comparator: Qwen3 through Apple Core AI

Apple's 2026 `coreai-models` tooling supports Qwen3 export for iOS and allows an app-bundled open model to conform to the same Foundation Models `LanguageModel` abstraction.

A Qwen3-0.6B path is therefore a useful later comparator for reproducibility/provider independence after the system-model baseline works.

Public references:

- https://github.com/apple/coreai-models
- https://developer.apple.com/documentation/foundationmodels/running-a-core-ai-model-in-a-foundation-models-session

### Local TTS: Pocket TTS through FluidAudio

Kyutai Pocket TTS is approximately 100M parameters, supports Spanish, streaming synthesis and local voice cloning. FluidAudio currently provides a Swift/CoreML path with Spanish and Spanish-24-layer packs plus voice cloning from short reference audio.

This is a particularly relevant first mobile TTS experiment because it tests both local synthesis and local voice identity without a commercial speech API.

Public references:

- https://kyutai.org/blog/2026-05-04-pocket-tts-multilingual/
- https://github.com/kyutai-labs/pocket-tts
- https://github.com/FluidInference/FluidAudio
- https://github.com/FluidInference/FluidAudio/blob/main/Documentation/TTS/PocketTTS.md

Any cloned research/demo voice must be explicitly consented and its provenance recorded. No participant voice should be turned into a reusable synthesis profile merely because the technical system makes that easy.

## Tokenizer-free TTS comparator: VoxCPM

VoxCPM is a separate TTS family that generates continuous speech representations rather than discrete audio tokens.

Its architecture is relevant to the wider mobile speech evaluation, but its versions have different practical roles:

- VoxCPM-0.5B and VoxCPM1.5 are relatively small but currently Chinese/English only;
- VoxCPM2 is 2B and supports 30 languages including Spanish, plus voice design/cloning;
- VoxCPM2 now has an on-device/edge `llama.cpp-omni` GGUF path with CPU/Metal support.

The official project reports about RTF 1.76 for Q8 inference on an Apple M4 Pro. That makes it worth benchmarking, but it does not establish acceptable realtime performance on an iPhone. It should therefore follow, not block, the lighter Pocket TTS proof.

Public reference:

- https://github.com/OpenBMB/VoxCPM

## Interruption: test cascaded barge-in before full speech-to-speech

The existing production architecture correctly treats participant interruption as potentially important while leaving full duplex unproven.

A useful intermediate experiment is **interruptible cascaded conversation**:

1. system TTS is playing;
2. microphone remains active through platform echo-cancellation / voice-processing audio;
3. local VAD detects participant speech;
4. playback is cancelled promptly;
5. the participant retains the floor;
6. streaming ASR continues the new turn.

This tests the interactional property we care about — participant ability to interrupt a mistaken or premature system turn — without making a full-duplex speech-language model an architectural prerequisite.

The system's own end-of-turn policy must remain conservative for collective-memory capture. Silence is not a network delay to optimise away.

## What this project must keep separate

Even if the technical substrate is eventually shared, this project owns its own requirements for:

- source audio as primary captured material;
- ASR transcript as derivation;
- exact mediation history;
- participant-led interview policy;
- conservative floor management;
- consent and withdrawal;
- relational privacy;
- archive blindness;
- research provenance;
- capture/archive/access privilege separation.

A commercial storytelling runtime must not define those rules.

## Code-sharing boundary

Do not make this public repository depend on a proprietary commercial repository merely to avoid duplicate work.

The current approach is:

1. allow the private proof to establish whether the generic mobile conversation architecture actually works;
2. keep the generic audio/session/model interfaces deliberately separable from product logic;
3. independently validate the same requirements against this project's research constraints;
4. if both projects genuinely require the same stable generic substrate, make an explicit later decision to extract or publish that generic subset under an appropriate licence.

That extraction should contain technical runtime only — audio lifecycle, model interfaces, event schemas, interruption and instrumentation — not storytelling logic or collective-memory research policy.

## Shared proof acceptance criteria relevant here

A useful first proof should run on a physical supported iPhone with the network disabled after assets are installed and demonstrate:

- live Spanish microphone input;
- streaming partial/final ASR;
- local multi-turn model response;
- local Spanish TTS;
- participant barge-in cancelling TTS;
- measured end-to-end latency;
- measured peak memory and thermal behaviour;
- explicit model/version provenance;
- no hidden network dependency.

For this project specifically, later evaluation must additionally measure:

- whether endpointing cuts off continuation;
- whether interruption works for slower or hesitant speech;
- ASR failures on names/places and Rioplatense forms;
- whether synthetic speech changes participant willingness to continue;
- whether the local model maintains the existing interviewer constraints;
- whether local-only operation materially improves the actual privacy/threat model rather than merely relocating sensitive data to an inadequately protected phone.

No production choice follows automatically from a successful engineering proof.
