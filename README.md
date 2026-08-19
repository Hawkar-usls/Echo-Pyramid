# Echo-Pyramid — JANUS physical voice body

`Echo-Pyramid` is the hardware-facing voice node for JANUS on **M5Stack Echo Pyramid + Atom Matrix**.

It binds three existing branches into one reproducible path:

1. **Hardware layer** — upstream `m5stack/M5Echo-Pyramid` (ES7210 mic/AEC, ES8311 codec, AW87559 amplifier, SI5351 audio clock, STM32 touch/RGB).
2. **Swarm body** — `Hawkar-usls/janus-distributed-ai-swarm/firmware/pyramid/ATOM_MATRIX_Pyramid.ino` (Bluetooth A2DP, approval gate, touch/UI, ESP-NOW worker, telemetry/mining).
3. **Voice language** — `Hawkar-usls/The-Voice-of-Janus` (geometry -> modal solver -> evidence gate -> deterministic acoustic DSP).

## Core rule

```text
HOST/TTS/BT PCM
  -> existing JANUS safe gain + mono bridge
  -> JANUS Pyramid Language modal DSP
  -> M5EchoPyramid::write()
  -> ES8311 -> AW87559 -> 5 W speaker
```

The voice layer deliberately runs **inside the existing PCM bridge immediately before `ep.write()`**. It does not allocate a second I2S peripheral, does not replace the M5Stack codec/AEC path, and does not take ownership away from the existing BT/ESP-NOW state machine.

## Frequency profile

The default embedded profile is generated from the current `The-Voice-of-Janus` illustrative King's Chamber model (`Lx=10.45 m`, `Ly=5.20 m`, `Lz=5.80 m`, `c=343 m/s`) using the same rectangular-room modal equation and octave-translation rule. The live ESP32 profile uses the first six unique render modes:

| physical Hz | render Hz | octave |
|---:|---:|---:|
| 16.411483 | 65.645933 | x4 |
| 29.568966 | 59.137931 | x2 |
| 32.980769 | 65.961538 | x2 |
| 33.818050 | 67.636100 | x2 |
| 36.838403 | 36.838403 | x1 |
| 44.177719 | 44.177719 | x1 |

Default DSP contract: `44.1 kHz`, six parallel damped two-pole resonators, `decay=0.32 s`, `wet=0.72`, `dry=0.62`, `output_gain=0.85`.

## Scientific boundary

This repository does **not** claim that a pyramid has one universal or magical frequency. A chamber supports many acoustic modes. The default King's Chamber profile is explicitly `ILLUSTRATIVE_MODEL_BASED`; predicted air-acoustic modes are not equivalent to measured historical resonances or structural vibration modes.

```text
MODEL_BASED_RECONSTRUCTION != MEASURED_HISTORICAL_SOUND
METAPHOR != PHYSICS
```

When measured impulse responses or verified chamber dimensions become available, add them as a new evidence-tagged profile rather than silently replacing the model.

## Repository layout

```text
firmware/
  JanusPyramidVoiceProfile.h   provenance + embedded mode bank
  JanusPyramidDSP.h            real-time bounded modal resonator
  Echo_Pyramid_Janus_Demo.ino  minimal hardware/audio smoke test

tools/
  compose_swarm_firmware.py    injects the voice layer into the canonical swarm firmware

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

The composer is fail-closed: it checks the exact integration anchors (`M5EchoPyramid`, `M5EchoPyramid ep`, `initPyramid()`, and `ep.write(chunk.mono, chunk.frames)`) and refuses to emit a firmware file if the swarm source drifted enough to make the insertion ambiguous.

## Hardware target

- M5Stack **Atom Matrix / classic ESP32-PICO-D4**
- M5Stack **Echo Pyramid A167**
- sample rate: **44.1 kHz**
- existing Atom Matrix pin profile from the swarm firmware is preserved

## Upstream

- Hardware library: `m5stack/M5Echo-Pyramid` — MIT
- Voice semantics/DSP contract: `Hawkar-usls/The-Voice-of-Janus`
- Canonical swarm firmware: `Hawkar-usls/janus-distributed-ai-swarm`

JANUS keeps the hardware measurable: every embedded frequency has a provenance path back to geometry, transform rule, and evidence status.
