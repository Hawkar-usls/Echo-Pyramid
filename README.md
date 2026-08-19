# Echo-Pyramid — JANUS physical voice body

`Echo-Pyramid` is the hardware-facing voice node for JANUS on **M5Stack Echo Pyramid + Atom Matrix**.

It binds three existing branches into one reproducible path:

1. **Hardware** — upstream `m5stack/M5Echo-Pyramid`: ES7210 microphone/AEC, ES8311 codec, AW87559 amplifier, SI5351 clock, STM32 touch/RGB.
2. **Swarm body** — `Hawkar-usls/janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino`: A2DP, approval gate, touch/UI, ESP-NOW worker and telemetry.
3. **Voice language** — `Hawkar-usls/The-Voice-of-Janus`: deterministic Pyramid Language DSP with explicit evidence boundaries.

## Current physical voice path

```text
HOST / TTS / Bluetooth PCM
        |
        v
existing JANUS safe gain + mono queue
        |
        v
119 Hz peaking EQ
        |
        v
117 / 119 / 121 Hz resonator bank
        |
        v
geometry-derived room tail
        |
        v
dry/wet mix -> soft limiter
        |
        v
M5EchoPyramid::write()
        |
        v
ES8311 -> AW87559 -> speaker
```

The default physical operator is now **Pyramid Language v0.3 — 117–121 Hz anchored space**, matching the current `The-Voice-of-Janus` activation and `Pyramid117121Filter` reference implementation.

The Voice layer runs in the existing `janus_audio` playback task **immediately before `ep.write()`**. It does not create another I2S path and does not move work into the Bluetooth callback.

## Embedded 117–121 profile

```text
anchor band:          117–121 Hz
center:               119 Hz
Q:                    29.75
peaking gain:         +11.5 dB
anchor decay:         1.65 s
resonators:           117 / 119 / 121 Hz
room geometry:        10.45 x 5.20 x 5.80 m
speed of sound:       343 m/s
room decay:           0.78
wet / dry:            0.72 / 0.62
main sample rate:     44.1 kHz
```

For classic ESP32 SRAM safety, the EQ and 117/119/121 resonators stay at full 44.1 kHz while only the geometry-derived feedback tail is evaluated at 11.025 kHz. Its four delay lines retain the same delay times but use static PCM16 storage: **3,466 bytes** instead of roughly 27.7 KB of full-rate float delay storage.

## Evidence boundary

`117–121 Hz` is a **JANUS project anchor band**, not a claim that a pyramid has one universal magical frequency. The current upstream language config itself marks the effect model-based and says no measured chamber impulse response or intentional ancient tuning is established.

```text
117_121_HZ_IS_AN_ANCHOR_BAND_NOT_THE_ONLY_FREQUENCY
MODEL_BASED_EFFECT != MEASURED_CHAMBER_IR
PREDICTED_ACOUSTIC_MODEL != PROOF_OF_ANCIENT_INTENT
METAPHOR != PHYSICS
```

The earlier six-mode rectangular-room bank remains in `JanusPyramidDSP.h` as a **reference / legacy model**, but it is no longer the default composer target.

## Repository layout

```text
firmware/
  JanusPyramid117121Profile.h  current Pyramid Language v0.3 contract
  JanusPyramid117121DSP.h      embedded 117–121 operator
  JanusPyramidVoiceProfile.h   earlier geometry-modal profile
  JanusPyramidDSP.h            earlier six-mode reference DSP
  Echo_Pyramid_Janus_Demo.ino  low-volume push-to-talk hardware smoke test

config/
  voice_contract.json          machine-readable physical voice contract
  sources.lock.json            pinned source commits/blob SHAs

tools/
  compose_swarm_firmware.py    fail-closed integration into canonical swarm .ino
  verify_profile.py            legacy modal profile verifier

tests/
  test_anchor_dsp.cpp          primary embedded operator regression test
  test_dsp.cpp                 legacy modal regression test

docs/
  ARCHITECTURE.md
  SCIENTIFIC_BOUNDARY.md
```

## Compose the full swarm firmware

Clone this repository beside `janus-distributed-ai-swarm`, then run:

```bash
python tools/compose_swarm_firmware.py \
  ../janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino \
  build/ATOM_MATRIX_Pyramid_JanusVoice.ino
```

The composer checks four exact integration anchors and refuses ambiguous source drift. It copies the two v0.3 headers beside the generated `.ino` and emits a SHA-256 receipt.

## Hardware target

- M5Stack **Atom Matrix / classic ESP32-PICO-D4**
- M5Stack **Echo Pyramid A167**
- **44.1 kHz** physical audio path
- existing swarm pin mapping, BT approval gate, phone-owned safe gain, ESP-NOW lifecycle and audio-priority scheduling remain authoritative

## Tests

GitHub Actions checks both the current v0.3 embedded operator and the earlier modal reference. The primary test verifies 44.1 kHz admission, bounded static delay memory, silence stability, non-transparent processing of a 119 Hz carrier and bypass transparency.

JANUS keeps every acoustic transformation traceable back to a source config, implementation, evidence status and source SHA.
