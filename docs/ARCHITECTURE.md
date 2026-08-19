# Echo-Pyramid architecture

## Canonical inputs

At integration time the canonical Pyramid swarm body was observed as:

```text
repository: Hawkar-usls/janus-distributed-ai-swarm
path:       firmware/pyramid/ATOM_MATRIX_Pyramid.ino
blob:       3b514eddd6486430c74c09c1d850483175de045a
```

The hardware abstraction is provided by `m5stack/M5Echo-Pyramid`.
The language contract and reference DSP are provided by `Hawkar-usls/The-Voice-of-Janus`.

## Existing audio path

The swarm firmware already has the correct ownership model:

```text
Bluetooth A2DP decoded stereo PCM
        |
        v
janusA2dpPcmCallback()
  - L/R -> mono
  - phone-owned safe gain curve
  - soft limit
  - enqueue JanusAudioChunk (256 frames)
        |
        v
FreeRTOS janus_audio playback task
        |
        v
ep.write(chunk.mono, chunk.frames)
        |
        v
M5Echo-Pyramid I2S/codec/amplifier
```

The Voice-of-Janus layer is inserted in the playback task:

```cpp
janusVoiceDsp.processInPlace(chunk.mono, chunk.frames);
ep.write(chunk.mono, chunk.frames);
```

## Why the DSP is not run inside the A2DP callback

The Bluetooth callback should remain short and predictable. The existing firmware deliberately moves PCM into a queue and lets a dedicated task perform hardware writes. Running the modal bank in that task preserves the same scheduling boundary and avoids adding floating-point work to the Bluetooth callback context.

This also keeps the existing responsibilities intact:

- Bluetooth approval/trusted-peer gate remains authoritative.
- phone volume remains the owner of the existing safe PCM gain curve.
- `M5EchoPyramid::begin()` remains the owner of I2S.
- ESP-NOW lifecycle and exclusive-radio policy are unchanged.
- LED/audio telemetry continues to use the pre-existing PCM bridge.
- no second I2S channel is created.

## Embedded DSP

`firmware/JanusPyramidDSP.h` is intentionally header-only and bounded:

- six parallel damped two-pole resonators;
- no dynamic allocation;
- fixed-size state arrays;
- mono PCM16 input/output;
- 44.1 kHz default sample rate;
- state reset on enable/disable transition;
- bounded fast soft limiter.

At 44.1 kHz the six-mode bank performs roughly `6 * 44100 = 264600` resonator state updates per second. This is deliberately smaller than the eight-mode offline default in order to match the six-mode live-microphone contract and leave headroom for Bluetooth, UI and swarm work on classic ESP32.

## Composer

`tools/compose_swarm_firmware.py` derives a build artifact from the canonical swarm sketch instead of duplicating a large, fast-moving firmware body.

It refuses to compose unless each of these anchors is unique:

```text
#include <M5EchoPyramid.h>
M5EchoPyramid ep;
  initPyramid();
        ep.write(chunk.mono, chunk.frames);
```

It then injects:

1. `JanusPyramidDSP.h` include;
2. one global DSP instance;
3. `begin(EP_SAMPLE_RATE)` immediately after Pyramid init;
4. in-place processing immediately before the canonical `ep.write()` call.

The output directory receives both headers and a SHA-256 JSON composition receipt. The canonical source is never overwritten.

## Physical chain

```text
MIC path: ES7210 -> I2S RX -> Atom Matrix -> optional DSP -> I2S TX -> ES8311 -> AW87559 -> speaker
BT path:  A2DP PCM -------------------------> optional DSP -> I2S TX -> ES8311 -> AW87559 -> speaker
```

The M5Stack library remains responsible for SI5351 MCLK, codec initialization, ADC input, STM32 touch/RGB and amplifier access.

## Future profiles

Do not overwrite the model profile with a new frequency list. Add a new profile with provenance and one of these evidence classes:

```text
ILLUSTRATIVE_MODEL_BASED
SOURCE_VERIFIED_GEOMETRY_MODEL
MEASURED_ROOM_RESPONSE
MEASURED_DEVICE_RESPONSE
```

A measured impulse response should become a distinct implementation/profile because convolution of a measured IR is a different evidence object from a synthetic modal bank.
