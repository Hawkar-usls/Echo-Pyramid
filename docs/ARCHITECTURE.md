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

The canonical acoustic-language identity is:

```text
PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3
```

The bounded physical implementation is independently revisioned as:

```text
PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2
```

A physical implementation revision does not silently change the language parameters.

## Authority split

```text
text / semantics
      |
      v
The-Voice-of-Janus / DemiHead larynx
      |
      v
ordinary PCM carrier
      |
      v
Echo-Pyramid physical Pyramid Language executor
      |
      v
M5 Echo Pyramid speaker hardware
```

The larynx defines articulation/timbre upstream. The physical Pyramid does not select the neural TTS speaker and the larynx does not own the physical 117–121 Hz acoustic operator.

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
Pyramid Language physical DSP
        |
        v
ep.write(chunk.mono, chunk.frames)
        |
        v
M5Echo-Pyramid I2S / codec / amplifier
```

The Pyramid Language operator is inserted only in the playback task:

```cpp
janusVoiceProcessChunk(chunk.mono, chunk.frames);
ep.write(chunk.mono, chunk.frames);
```

This keeps the Bluetooth callback short, leaves `M5EchoPyramid::begin()` as the sole I2S owner, and does not alter BT approval, phone volume ownership, ESP-NOW lifecycle, mining policy or the existing PCM queue.

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

## ESP32-r2 room-tail adaptation

The reference implementation uses floating-point feedback-delay arrays at the full 44.1 kHz rate. A literal delay-bank copy would consume roughly 27.7 KB only for delay samples, undesirable beside Classic BT and ESP-NOW on Atom Matrix.

The embedded port therefore keeps the frequency-critical path at **44.1 kHz**:

- 119 Hz peaking EQ: full rate;
- 117/119/121 Hz resonators: full rate;
- final dry/wet mix and limiter: full rate.

Only the room tail is evaluated every fourth audio sample, at an effective **11.025 kHz**. Geometric delay times remain equivalent:

```text
2*10.45 m round trip -> 672 samples @ 11025 Hz
2*5.20 m round trip  -> 334 samples @ 11025 Hz
2*5.80 m round trip  -> 373 samples @ 11025 Hz
(5.20+5.80) m path   -> 354 samples @ 11025 Hz
```

Total delay storage is:

```text
1733 PCM16 samples = 3466 bytes
```

### Decimated damping correction

The reference delay recurrence uses damping coefficient `0.22` at 44.1 kHz. Reusing `0.22` unchanged while updating the delay only every fourth sample would change its wall-clock persistence.

`ESP32-r2` therefore uses:

```text
d_embedded = d_source^4
           = 0.22^4
           = 0.00234256
```

This preserves the recurrence pole approximately across four reference-rate sample intervals. It is an embedded approximation, not a claim of bit-identical parity with the Python room-tail implementation.

## Runtime depth

`JanusPyramid117121DSP` exposes a physical-space depth control:

```cpp
janusVoiceDsp.setAmountPercent(0..100);
```

Semantics:

```text
100% -> canonical v0.3 effect
 50% -> source/effect crossfade midpoint
  0% -> dry output while DSP acoustic state still advances
OFF  -> hard bypass / no DSP processing
```

Depth changes ramp over one PCM block. Runtime depth is allowed to tune physical listening intensity without changing the canonical 117/119/121 Hz, Q, gain, decay, geometry or wet/dry language constants.

## Real-time measurement boundary

For 256 frames at 44.1 kHz:

```text
PCM block duration ~= 5804 us
```

The composed runtime measures each DSP invocation:

```text
dsp_ema_us
dsp_peak_us
dsp_load_percent
```

and emits a 10-second status report with free heap, depth and failsafe state.

Host C++ timing is not accepted as proof of physical Atom Matrix timing. The final performance authority is the device itself while its normal Bluetooth/swarm workload is active.

## Audio-budget failsafe

The physical invariant is:

```text
AUDIO_CONTINUITY_HAS_PRIORITY_OVER_EFFECT
```

Default guard:

```text
JANUS_PYRAMID_DSP_FAILSAFE = 1
JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP = 3
```

For each chunk, the runtime compares measured DSP processing time with that chunk's PCM duration. Three consecutive over-budget chunks set `janusVoiceBudgetTrip`.

The audio task then stops processing future chunks immediately, so queued source PCM remains dry and can continue toward `ep.write()` without another expensive DSP call. The main loop performs the one-time resonator/delay reset by disabling the DSP outside the high-priority playback task.

```text
3 consecutive DSP overruns
       |
       v
janusVoiceBudgetTrip = true
       |
       +--> future audio chunks: untouched dry PCM
       |
       v
main loop janusVoiceSafetyTick()
       |
       v
setEnabled(false) + state reset
```

No language parameter is altered in response to CPU load. The effect is disabled instead of being silently retuned. There is no automatic retry loop; explicit `PYR=ON` or reboot clears the trip.

## Local USB tuning ownership

The current pinned swarm source does not consume Serial input. The composer may therefore inject a local USB A/B console:

```text
PYR?
PYR=0..100
PYR=ON
PYR=OFF
```

This is not network control.

The composer scans for base-firmware Serial input owners such as `Serial.available()` and `Serial.read()`. If one exists, the normal composition fails closed rather than creating two consumers for one byte stream.

Intentional fallback:

```text
--no-usb-control
```

This disables the Pyramid Serial parser while preserving DSP, real-time telemetry and the autonomous audio-budget failsafe.

## Composer ownership and source drift

`tools/compose_swarm_firmware.py` derives a build artifact instead of committing a stale duplicate of the large swarm sketch. It requires exactly one occurrence of each structural anchor:

```text
#include <M5EchoPyramid.h>
M5EchoPyramid ep;
  initPyramid();
        ep.write(chunk.mono, chunk.frames);
  serialStatus();
```

It injects:

1. current `JanusPyramid117121DSP.h`;
2. physical runtime/telemetry/failsafe state;
3. `begin(EP_SAMPLE_RATE)` immediately after Pyramid initialization;
4. timed DSP immediately before the existing `ep.write()`;
5. main-loop safety/status hooks;
6. local USB control only when Serial input has no pre-existing owner.

The canonical swarm source is never overwritten.

## Pinned composition workflow

`.github/workflows/compose-firmware.yml` performs an independent source-bundle build:

```text
checkout Echo-Pyramid
 -> checkout canonical swarm
 -> verify pinned swarm Git blob
 -> verify unique integration anchors
 -> verify Serial ownership observation
 -> run composer
 -> verify DSP + failsafe + receipt invariants
 -> upload Arduino source bundle
```

The uploaded bundle contains the composed `.ino`, current DSP/profile headers and the SHA-256 composition receipt.

## Provenance layers

`config/sources.lock.json` records observed hardware, swarm and language source blobs.

`config/the_voice_of_janus.runtime_lock.json` pins the exact physical contract/profile/DSP/composer blobs against the unchanged language v0.3 reference.

`tools/verify_runtime_lock.py` recalculates local Git blob hashes; `tools/verify_swarm_checkout.py` performs the equivalent check against an independently checked-out swarm sketch before composition.

## Physical chain

```text
MIC: ES7210 -> I2S RX -> Atom Matrix -> Pyramid Language -> budget guard -> I2S TX -> ES8311 -> AW87559 -> speaker
BT:  A2DP PCM -----------------------> Pyramid Language -> budget guard -> I2S TX -> ES8311 -> AW87559 -> speaker
```

## Physical acceptance gate

The exact device procedure is in `docs/HARDWARE_TEST_PROTOCOL.md`.

Until measurements come back from the real Atom Matrix + Echo Pyramid:

```text
CODE_PATH = IMPLEMENTED
HOST_REGRESSION = IMPLEMENTED
COMPOSE_PIPELINE = IMPLEMENTED
PHYSICAL_REALTIME_GATE = PENDING_DEVICE_MEASUREMENT
```

## Reference / legacy operator

`JanusPyramidDSP.h` + `JanusPyramidVoiceProfile.h` preserve the earlier six-mode rectangular-room bank. It remains useful for comparison/regression but is not the current composer default.

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
