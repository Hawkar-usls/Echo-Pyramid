# Echo-Pyramid — JANUS physical voice body

`Echo-Pyramid` is the hardware-facing voice node for JANUS on **M5Stack Echo Pyramid + Atom Matrix**.

It binds three independent authorities into one reproducible physical voice path:

1. **Hardware** — `m5stack/M5Echo-Pyramid`: ES7210 microphone/AEC, ES8311 codec, AW87559 amplifier, SI5351 clock and STM32 touch/RGB.
2. **Swarm body** — `Hawkar-usls/janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino`: A2DP, approval gate, touch/UI, ESP-NOW worker, telemetry and audio-priority scheduling.
3. **Voice language** — `Hawkar-usls/The-Voice-of-Janus`: larynx/TTS upstream plus the deterministic Pyramid Language acoustic operator.

The responsibilities stay separate:

```text
LARYNX / TTS / PHONE / MIC
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

The larynx may change without changing the Pyramid Language parameters. The physical Echo-Pyramid firmware does not define the human TTS timbre; it applies the acoustic space after the source voice exists.

## Current physical voice path

```text
ordinary JANUS voice / music / Bluetooth PCM
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

The source audio remains the carrier. Speech is not replaced by tones; music is not replaced by a synthetic drone. The intended transformation is:

```text
ORDINARY_AUDIO_PCM
  -> SAME_SOURCE_AUDIO_WITH_PYRAMID_ACOUSTIC_COLORATION
```

The DSP runs inside the existing `janus_audio` playback task **immediately before `ep.write()`**. It does not create a second I2S owner and does not put floating-point room processing inside the Bluetooth callback.

## Language v0.3 vs embedded revision

The acoustic language remains:

```text
PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3
```

The current bounded physical implementation is:

```text
PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2
```

`ESP32-r2` is an implementation revision, not a new acoustic-language version. It adds runtime depth control, real-time timing telemetry, corrected damping for the decimated room tail, a dry audio-budget failsafe and fail-closed local USB tuning without changing the canonical 117–121 Hz language parameters.

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

For classic ESP32 SRAM/CPU safety, the EQ and 117/119/121 resonators stay at full **44.1 kHz** while only the geometry-derived feedback tail is evaluated at **11.025 kHz**. Its four delay lines retain the modeled delay times and use static PCM16 storage:

```text
672 + 334 + 373 + 354 = 1733 samples
1733 * 2 bytes = 3466 bytes
```

The reference feedback-delay damping is `0.22` at 44.1 kHz. Because one embedded room update spans four reference-rate samples, `ESP32-r2` uses the time-equivalent persistence coefficient:

```text
d_embedded = d_source^4 = 0.22^4 = 0.00234256
```

This keeps the decimated low-pass memory closer to the reference wall-clock decay instead of accidentally stretching it fourfold.

## Runtime Pyramid-space depth

The physical DSP exposes `setAmountPercent(0..100)`:

- `100%` — full canonical Pyramid Language v0.3 effect;
- `50%` — A/B-friendly halfway crossfade between original source and the full acoustic-space output;
- `0%` — original source at the output while the acoustic state remains running;
- hard bypass — DSP disabled entirely via `setEnabled(false)`.

Depth changes ramp over the next PCM block to avoid an abrupt discontinuity/click.

## Audio-budget failsafe

The effect is subordinate to clean audio transport:

```text
AUDIO_CONTINUITY_HAS_PRIORITY_OVER_EFFECT
```

At 44.1 kHz each 256-frame PCM block represents roughly **5804 µs**. `ESP32-r2` measures the actual DSP processing time per block. The default guard is:

```text
JANUS_PYRAMID_DSP_FAILSAFE = 1
JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP = 3
```

If three consecutive processed blocks require at least their full PCM time budget, the physical layer trips to **dry bypass**. Future queued PCM is left untouched immediately; resonator/delay state is then reset from the main loop rather than performing a large reset inside `janus_audio`.

Expected event:

```text
PYRAMID_LANGUAGE_FAILSAFE | DRY_BYPASS reason=DSP_OVER_BUDGET ...
```

There is deliberately no automatic parameter mutation and no automatic retry loop. The canonical 117/119/121 Hz language remains unchanged. An explicit `PYR=ON` or a reboot clears the trip.

## USB A/B tuning on the real Pyramid

When the base swarm firmware does not already consume Serial input, the composer enables a tiny **local USB-only** tuning console:

```text
PYR?        report current DSP/failsafe state
PYR=0       dry output, DSP state still running
PYR=25      25% Pyramid-space depth
PYR=50      50% Pyramid-space depth
PYR=100     full Pyramid Language v0.3
PYR=OFF     hard bypass DSP
PYR=ON      clear failsafe trip and enable DSP
```

This is intentionally not network control. It exists so the same voice/music passage can be compared dry vs processed without reflashing or changing the phone volume.

Serial input has exactly one owner. If a future swarm firmware begins consuming `Serial.available()` / `Serial.read()`, the composer refuses the default USB-control integration. For an intentional shared build, compose with:

```bash
python tools/compose_swarm_firmware.py \
  ../janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino \
  build/ATOM_MATRIX_Pyramid_JanusVoice.ino \
  --no-usb-control
```

That mode keeps Pyramid Language DSP, timing telemetry and the autonomous audio-budget failsafe but does not consume Serial input.

## Real-time telemetry

The composed firmware emits a 10-second status line:

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

This is the decisive measurement gate for the real Atom Matrix. Host tests prove bounded code/state behavior; only device telemetry can tell us the real Bluetooth-era CPU margin on the physical ESP32.

## Compose the full swarm firmware

Normal current-source build:

```bash
python tools/compose_swarm_firmware.py \
  ../janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino \
  build/ATOM_MATRIX_Pyramid_JanusVoice.ino
```

The composer is fail-closed. It requires unique integration anchors, verifies Serial input ownership before enabling USB tuning, never overwrites the canonical swarm source, copies the two current DSP/profile headers beside the generated `.ino`, and emits a SHA-256 composition receipt.

## Generated source bundle

`.github/workflows/compose-firmware.yml` independently checks out the canonical swarm repository, verifies the pinned Pyramid sketch Git blob and integration anchors, composes the current physical runtime, validates the v2.5 receipt and uploads an Arduino source artifact named:

```text
JANUS-Echo-Pyramid-v0.3-ESP32-r2-source
```

The artifact contains the composed `.ino`, `JanusPyramid117121DSP.h`, `JanusPyramid117121Profile.h` and the composition receipt. The repository therefore does not need a second manually maintained 164-KB copy of the fast-moving swarm sketch.

## Provenance locks

`config/sources.lock.json` pins the observed hardware/swarm/language source blobs.

`config/the_voice_of_janus.runtime_lock.json` separately pins:

- canonical Pyramid Language v0.3 activation/reference implementation;
- current upstream larynx pointer without treating the larynx as the language;
- physical `ESP32-r2` contract/profile/DSP/composer blobs.

`tools/verify_runtime_lock.py` recomputes actual Git blob SHAs for local physical files and fails CI on silent drift. `tools/verify_swarm_checkout.py` applies the same principle to a checked-out canonical swarm sketch before composition.

## Repository layout

```text
firmware/
  JanusPyramid117121Profile.h  current v0.3 / ESP32-r2 profile
  JanusPyramid117121DSP.h      embedded real-time 117–121 operator
  Echo_Pyramid_Janus_Demo.ino  low-volume mic -> Pyramid -> speaker smoke test
  JanusPyramidVoiceProfile.h   earlier geometry-modal reference
  JanusPyramidDSP.h            earlier six-mode reference DSP

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
  test_dsp.cpp

docs/
  ARCHITECTURE.md
  HARDWARE_TEST_PROTOCOL.md
  SCIENTIFIC_BOUNDARY.md
```

## Hardware target

- M5Stack **Atom Matrix / classic ESP32-PICO-D4**
- M5Stack **Echo Pyramid A167**
- **44.1 kHz** physical audio path
- existing Atom Matrix Pyramid pin mapping
- existing BT approval gate, phone-owned safe gain, ESP-NOW lifecycle and audio-priority policy remain authoritative

## Evidence boundary

`117–121 Hz` is a **JANUS project acoustic anchor band**, not a claim that a pyramid has one universal magical frequency. The current language operator is model-based; no measured chamber impulse response or intentional ancient tuning is asserted.

```text
117_121_HZ_IS_AN_ANCHOR_BAND_NOT_THE_ONLY_FREQUENCY
MODEL_BASED_EFFECT != MEASURED_CHAMBER_IR
PREDICTED_ACOUSTIC_MODEL != PROOF_OF_ANCIENT_INTENT
METAPHOR != PHYSICS
```

A future measured room response should be added as a distinct evidence-tagged profile rather than silently mutating this model.

## Tests and current gate

GitHub Actions is configured to gate the repository on:

- pinned runtime-lock conformance;
- fail-closed composer behavior, including Serial ownership, `--no-usb-control` and budget-failsafe injection;
- current 117–121 DSP regression tests, including depth/bypass behavior and bounded static memory;
- earlier six-mode reference regression tests;
- composition of a source bundle from the pinned canonical swarm sketch.

The physical acceptance procedure is frozen in `docs/HARDWARE_TEST_PROTOCOL.md`. Until a real Atom Matrix + Echo Pyramid run provides timing, drop, heap and Bluetooth observations, status remains:

```text
CODE_PATH = IMPLEMENTED
HOST_REGRESSION = IMPLEMENTED
COMPOSE_PIPELINE = IMPLEMENTED
PHYSICAL_REALTIME_GATE = PENDING_DEVICE_MEASUREMENT
```
