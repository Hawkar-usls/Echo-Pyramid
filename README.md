# Echo-Pyramid — JANUS physical voice body

`Echo-Pyramid` is the hardware-facing JANUS voice node for **M5Stack Echo Pyramid + Atom Matrix**.

It joins three independent authorities without collapsing their responsibilities:

1. **Hardware** — `m5stack/M5Echo-Pyramid`: ES7210 microphone/AEC, ES8311 codec, AW87559 amplifier, SI5351 clock and STM32 touch/RGB.
2. **Swarm body** — `Hawkar-usls/janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino`: Bluetooth A2DP, approval gate, UI/touch, ESP-NOW worker and audio-priority scheduling.
3. **Voice language** — `Hawkar-usls/The-Voice-of-Janus`: larynx/TTS upstream and the deterministic Pyramid Language acoustic operator.

```text
TEXT / PHONE / MIC / MUSIC
          |
          v
ordinary source PCM
          |
          v
PYRAMID LANGUAGE v0.3
          |
          v
physical Echo Pyramid speaker path
```

The source remains the source: speech is not replaced by tones and music is not replaced by a synthetic drone.

```text
ORDINARY_AUDIO_PCM
  -> SAME_SOURCE_AUDIO_WITH_PYRAMID_ACOUSTIC_COLORATION
```

## Current physical path

```text
ordinary JANUS voice / music / Bluetooth PCM
        |
        v
existing JANUS safe gain + mono queue
        |
        v
janus_audio PCM block boundary
        |
        +--> apply queued Pyramid control request
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
runtime Pyramid-space depth crossfade
        |
        v
real-time audio budget guard
        |
        v
M5EchoPyramid::write()
        |
        v
ES8311 -> AW87559 -> speaker
```

The DSP runs in the existing `janus_audio` playback task immediately before `ep.write()`. It does **not** create a second I2S owner and does not move floating-point room processing into the Bluetooth callback.

## Language v0.3 and embedded revision

The acoustic language remains:

```text
PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3
```

The current bounded physical implementation is:

```text
PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2
```

`ESP32-r2` is an implementation revision, not a new language version. The canonical acoustic parameters stay fixed:

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

## Embedded room-tail adaptation

The EQ and 117/119/121 resonators stay at full **44.1 kHz**. Only the geometry-derived room tail is evaluated at **11.025 kHz** to bound classic ESP32 SRAM/CPU use.

```text
672 + 334 + 373 + 354 = 1733 PCM16 samples
1733 * 2 bytes = 3466 bytes
```

The reference delay damping is `0.22` at 44.1 kHz. `ESP32-r2` compensates for the four-sample room update interval with:

```text
d_embedded = d_source^4 = 0.22^4 = 0.00234256
```

This preserves the recurrence persistence more closely in wall-clock time instead of stretching it by the decimation factor.

## Runtime depth

The DSP exposes `setAmountPercent(0..100)`:

- `100%` — full canonical Pyramid Language v0.3 effect;
- `50%` — source/effect midpoint;
- `0%` — dry output while acoustic state still advances;
- hard bypass — DSP disabled entirely.

Depth changes ramp over the next PCM block to avoid an abrupt discontinuity.

## One owner for mutable DSP state

External control never resets resonators or delay buffers directly from `loopTask`/USB while `janus_audio` may be using them.

The physical runtime uses a `portMUX`-guarded request mailbox:

```text
USB / future local controller
        |
        v
pending enable / depth / failsafe-clear request
        |
        v
janus_audio takes request at next PCM block boundary
        |
        v
DSP mutable state changes under one runtime owner
```

Invariant:

```text
DSP_MUTABLE_STATE_HAS_ONE_RUNTIME_OWNER
```

`PYR?` reports both current and pending control state so a queued command is visible before the next audio block applies it.

## Audio-budget failsafe

The effect is subordinate to clean audio transport:

```text
AUDIO_CONTINUITY_HAS_PRIORITY_OVER_EFFECT
```

A 256-frame block at 44.1 kHz represents roughly **5804 µs**. The default guard is:

```text
JANUS_PYRAMID_DSP_FAILSAFE = 1
JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP = 3
```

Three consecutive DSP blocks at or above their PCM-time budget trip the physical layer to dry bypass. Future queued PCM is left untouched; a one-time DSP reset is performed from the main loop only after the trip guarantees new audio calls return dry.

```text
PYRAMID_LANGUAGE_FAILSAFE | DRY_BYPASS reason=DSP_OVER_BUDGET ...
```

No acoustic parameter is silently changed in response to load. `PYR=ON` queues an explicit failsafe clear + clean DSP re-enable at the next PCM block boundary; reboot also clears the trip.

## Local USB A/B control

When the canonical swarm firmware does not already consume Serial input, the composed runtime enables:

```text
PYR?        report current + pending DSP/failsafe state
PYR=0       queue dry-output depth
PYR=25      queue 25% Pyramid-space depth
PYR=50      queue 50% depth
PYR=100     queue full v0.3 depth
PYR=OFF     queue hard bypass
PYR=ON      queue failsafe clear + DSP enable
```

This is local USB tuning, **not network control**.

Serial input has one owner. If a future swarm firmware begins consuming `Serial.available()` / `Serial.read()`, the composer fails closed. Intentional fallback:

```bash
python tools/compose_swarm_firmware.py \
  ../janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino \
  build/ATOM_MATRIX_Pyramid_JanusVoice.ino \
  --no-usb-control
```

That mode preserves DSP, timing telemetry, the request mailbox and the autonomous audio-budget failsafe without consuming Serial input.

## Real-time telemetry

The composed runtime emits a 10-second summary:

```text
PYRAMID_LANGUAGE |
  enabled=1
  depth=100%
  failsafe=0
  trips=0
  anchor=117/119/121Hz
  dsp_ema_us=...
  dsp_peak_us=...
  budget_us=5804
  dsp_load=...%
  delay_bytes=3466
  heap=...
```

Only real-device telemetry can establish the physical Bluetooth-era CPU margin.

## Compose the full swarm firmware

```bash
python tools/compose_swarm_firmware.py \
  ../janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino \
  build/ATOM_MATRIX_Pyramid_JanusVoice.ino
```

The composer is fail-closed. It requires unique structural anchors, checks Serial-input ownership, never overwrites the canonical swarm source, copies the current DSP/profile headers beside the generated `.ino`, and emits a SHA-256 receipt.

Current receipt schema:

```text
janus.echo_pyramid.compose_receipt.v2.6
```

## Generated Arduino source bundle

`.github/workflows/compose-firmware.yml` independently:

```text
checkout Echo-Pyramid
 -> checkout canonical swarm
 -> verify pinned swarm Git blob + anchors
 -> verify Serial ownership observation
 -> compose current runtime
 -> verify portMUX mailbox + budget failsafe + v2.6 receipt
 -> upload source bundle
```

Artifact name:

```text
JANUS-Echo-Pyramid-v0.3-ESP32-r2-source
```

It contains the composed `.ino`, `JanusPyramid117121DSP.h`, `JanusPyramid117121Profile.h` and the composition receipt.

## Standalone hardware smoke test

`firmware/Echo_Pyramid_Janus_Demo.ino` uses the same `ESP32-r2` operator. Hold the Atom button for low-volume microphone loopback. Its USB console supports the same `PYR` A/B commands and reports `dsp_ema_us`, peak time and the 5804-µs block budget every two seconds.

Acoustic feedback is possible; keep volume low and the device away from ears.

## Provenance locks

`config/sources.lock.json` pins observed hardware/swarm/language source blobs.

`config/the_voice_of_janus.runtime_lock.json` pins:

- canonical Pyramid Language v0.3 activation/reference implementation;
- current upstream larynx pointer without treating larynx as language;
- physical `ESP32-r2` contract/profile/DSP/composer blobs;
- audio-task DSP ownership, failsafe and decimated room-tail invariants.

`tools/verify_runtime_lock.py` recalculates Git blob SHAs and validates those semantic invariants. `tools/verify_swarm_checkout.py` verifies an independently checked-out canonical swarm sketch before composition.

## Repository layout

```text
firmware/
  JanusPyramid117121Profile.h
  JanusPyramid117121DSP.h
  Echo_Pyramid_Janus_Demo.ino
  JanusPyramidVoiceProfile.h      # earlier reference
  JanusPyramidDSP.h               # earlier reference

config/
  voice_contract.json
  sources.lock.json
  the_voice_of_janus.runtime_lock.json

tools/
  compose_swarm_firmware.py
  verify_runtime_lock.py
  verify_swarm_checkout.py
  verify_profile.py

tests/
  test_anchor_dsp.cpp
  test_composer.py
  compile_composed_runtime.py
  test_dsp.cpp

docs/
  ARCHITECTURE.md
  HARDWARE_TEST_PROTOCOL.md
  SCIENTIFIC_BOUNDARY.md
```

## Test gates

GitHub Actions is configured to run:

- runtime-lock blob + semantic invariant verification;
- fail-closed composer regression tests;
- C++11 compile-smoke of the **generated runtime** with USB ON and OFF;
- current 117–121 DSP host regression;
- legacy reference regression;
- independent source-bundle composition from the pinned swarm sketch.

The physical acceptance procedure is frozen in `docs/HARDWARE_TEST_PROTOCOL.md`.

Until a real Atom Matrix + Echo Pyramid provides timing, drop, heap and Bluetooth observations:

```text
CODE_PATH = IMPLEMENTED
HOST_REGRESSION = IMPLEMENTED
COMPOSE_PIPELINE = IMPLEMENTED
PHYSICAL_REALTIME_GATE = PENDING_DEVICE_MEASUREMENT
```

## Evidence boundary

`117–121 Hz` is a **JANUS project acoustic anchor band**, not a claim that a pyramid has one universal magical frequency. The current operator is model-based; no measured chamber impulse response or intentional ancient tuning is asserted.

```text
117_121_HZ_IS_AN_ANCHOR_BAND_NOT_THE_ONLY_FREQUENCY
MODEL_BASED_EFFECT != MEASURED_CHAMBER_IR
PREDICTED_ACOUSTIC_MODEL != PROOF_OF_ANCIENT_INTENT
METAPHOR != PHYSICS
```

A future measured room response should be added as a distinct evidence-tagged profile rather than silently mutating this model.
