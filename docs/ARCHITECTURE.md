# Echo-Pyramid architecture

## Canonical inputs

Pinned revisions live in `config/sources.lock.json`. The swarm integration target is:

```text
repository: Hawkar-usls/janus-distributed-ai-swarm
path:       firmware/pyramid/ATOM_MATRIX_Pyramid.ino
blob:       3b514eddd6486430c74c09c1d850483175de045a
```

The hardware abstraction is `m5stack/M5Echo-Pyramid`. The current language authority is `Hawkar-usls/The-Voice-of-Janus`, specifically:

```text
configs/pyramid_117_121_space.activation.json
src/pyramid_anchor_filter.py::Pyramid117121Filter
```

## Existing swarm audio ownership

```text
Bluetooth A2DP decoded stereo PCM
        |
        v
janusA2dpPcmCallback()
  - L/R -> mono
  - phone-owned safe gain
  - soft limit
  - enqueue 256-frame JanusAudioChunk
        |
        v
FreeRTOS janus_audio playback task
        |
        v
ep.write(chunk.mono, chunk.frames)
        |
        v
M5Echo-Pyramid I2S / codec / amplifier
```

The Pyramid Language operator is inserted only in the playback task:

```cpp
janusVoiceDsp.processInPlace(chunk.mono, chunk.frames);
ep.write(chunk.mono, chunk.frames);
```

This keeps the Bluetooth callback short, leaves `M5EchoPyramid::begin()` as the sole I2S owner, and does not alter BT approval, phone volume ownership, ESP-NOW lifecycle, mining policy or LED telemetry.

## Current Pyramid Language v0.3 operator

The embedded implementation is `firmware/JanusPyramid117121DSP.h`.

Reference order from `The-Voice-of-Janus`:

```text
DRY AUDIO
 -> 119 Hz RBJ peaking EQ (+11.5 dB, Q 29.75)
 -> 117 / 119 / 121 Hz damped resonator bank (1.65 s)
 -> geometry-derived feedback-delay room tail
 -> dry/wet mix (0.62 / 0.72)
 -> soft limit
```

The source audio remains the carrier; the DSP colours it rather than replacing speech/music with synthetic tones.

## ESP32 room-tail adaptation

The Python reference uses floating-point feedback-delay arrays at the full audio sample rate. Copying that literally would consume roughly 27.7 KB only for delay samples, which is undesirable beside Classic BT and ESP-NOW on Atom Matrix.

The embedded port therefore preserves the high-value frequency path at **44.1 kHz**:

- 119 Hz peaking EQ: full rate;
- 117/119/121 resonators: full rate;
- final dry/wet mix and limiter: full rate.

Only the room tail is decimated by four to **11.025 kHz**. Its delay times are preserved from the same geometry and speed of sound:

```text
2*10.45 m round trip -> 672 samples @ 11025 Hz
2*5.20 m round trip  -> 334 samples @ 11025 Hz
2*5.80 m round trip  -> 373 samples @ 11025 Hz
(5.20+5.80) m path   -> 354 samples @ 11025 Hz
```

Total delay storage is **1733 PCM16 samples = 3466 bytes**. A compiled host C++11 smoke test reports the complete DSP object at **3640 bytes**.

This is an embedded approximation of the reference room-tail implementation, not a bit-identical port. The anchor EQ/resonator parameters and geometric delay times remain traceable in `JanusPyramid117121Profile.h`.

## Composer

`tools/compose_swarm_firmware.py` derives a build artifact instead of committing a stale duplicate of the large swarm sketch. It is fail-closed and requires exactly one occurrence of each integration anchor:

```text
#include <M5EchoPyramid.h>
M5EchoPyramid ep;
  initPyramid();
        ep.write(chunk.mono, chunk.frames);
```

It injects:

1. `JanusPyramid117121DSP.h`;
2. one global `JanusPyramid117121DSP` instance;
3. `begin(EP_SAMPLE_RATE)` immediately after `initPyramid()`;
4. in-place DSP immediately before the existing `ep.write()`.

The generated folder receives the v0.3 DSP/profile headers and a SHA-256 composition receipt. The canonical swarm source is never overwritten.

## Physical chain

```text
MIC: ES7210 -> I2S RX -> Atom Matrix -> Pyramid Language -> I2S TX -> ES8311 -> AW87559 -> speaker
BT:  A2DP PCM -----------------------> Pyramid Language -> I2S TX -> ES8311 -> AW87559 -> speaker
```

## Reference / legacy operator

`JanusPyramidDSP.h` + `JanusPyramidVoiceProfile.h` preserve the earlier six-mode rectangular-room bank. It remains useful for comparison and regression testing but is not the current composer default.

## Future evidence profiles

Add rather than overwrite:

```text
ILLUSTRATIVE_MODEL_BASED
SOURCE_VERIFIED_GEOMETRY_MODEL
MODEL_BASED_117_121_HZ_ANCHORED_EFFECT
MEASURED_ROOM_RESPONSE
MEASURED_DEVICE_RESPONSE
```

A measured impulse response should become its own profile/implementation because measured convolution and a synthetic feedback-delay model are different evidence objects.
