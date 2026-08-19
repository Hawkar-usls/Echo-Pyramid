# Echo-Pyramid physical acceptance protocol

This protocol validates the **physical** `PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2` path on M5Stack Atom Matrix + Echo Pyramid.

It is intentionally separate from host C++ tests. Host tests prove deterministic code behavior and bounded state; this protocol measures whether the real classic ESP32 can sustain the effect while Bluetooth, I2S, UI and the existing JANUS swarm runtime are active.

## Acceptance principle

```text
AUDIO_CONTINUITY_HAS_PRIORITY_OVER_EFFECT
```

If the Pyramid DSP cannot meet the real-time PCM budget, the correct behavior is **dry audio**, not stutter, queue starvation, A2DP instability or silent mutation of the canonical 117–121 Hz language parameters.

## Preparation

Use the composed Arduino source bundle produced from the pinned swarm source. Keep the same:

- phone/source device;
- Bluetooth connection;
- source track or voice sample;
- phone volume;
- physical Pyramid placement;
- listening position;
- swarm/radio configuration.

Do not compare different tracks or compensate perceived loudness by moving the phone volume between A/B states. The point is to isolate the acoustic operator.

Open the existing 115200-baud Serial console and confirm boot reports:

```text
JANUS PYRAMID LANGUAGE | ok=1
profile=PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2
sr=44100
depth=100%
failsafe=1
trip_blocks=3
```

Also confirm the Pyramid itself initialized and normal Bluetooth playback works before evaluating the effect.

## Stage 1 — dry transport baseline

Play the chosen source and send:

```text
PYR=OFF
PYR?
```

Record at least 30 seconds of Serial observations.

Baseline requirements:

- Bluetooth remains connected;
- no new audible discontinuity attributable to the Pyramid layer;
- existing `janusAudioDropChunks` does not begin climbing persistently;
- free heap remains stable enough for the existing swarm firmware;
- Pyramid Language reports `enabled=0`.

This is the transport/control baseline, not an acoustic-language test.

## Stage 2 — live dry crossfade state

Send:

```text
PYR=ON
PYR=0
```

At `0%`, the DSP state continues running while the output crossfade is dry. This lets us measure the **CPU cost of the complete acoustic operator without hearing its wet result**.

Observe at least three 10-second `PYRAMID_LANGUAGE` reports.

Record:

```text
dsp_ema_us
dsp_peak_us
budget_us
dsp_load
failsafe
trips
heap
janusAudioDropChunks
Bluetooth continuity
```

For 256 frames at 44.1 kHz, `budget_us` should be about `5804`.

A `PYR=0` timing run is especially useful because audible differences cannot distract from judging scheduling health.

## Stage 3 — acoustic A/B ladder

Use the exact same passage and source volume. Switch only Pyramid depth:

```text
PYR=0
PYR=25
PYR=50
PYR=75
PYR=100
```

At each depth, listen long enough for speech consonants, vowels, bass energy and the room tail to be judged.

Expected behavior:

- source identity remains recognizable at every depth;
- words remain intelligible;
- the 117–121 Hz anchor is a coloration/resonance inside the source, not a replacement tone;
- increasing depth increases the perceived modeled space continuously rather than causing a discontinuous preset jump;
- `PYR=100` is the canonical v0.3 physical effect.

A practical first preference is **not** automatically 100%. If the physical speaker/enclosure makes the canonical effect too dominant, record that observation rather than silently changing the v0.3 language constants. Runtime depth is the allowed physical listening control.

## Stage 4 — sustained full-effect run

Set:

```text
PYR=100
```

Play continuously for at least several minutes while the normal JANUS runtime remains active.

Watch:

- `dsp_ema_us`;
- `dsp_peak_us`;
- `dsp_load`;
- `failsafe` / `trips`;
- `janusAudioDropChunks`;
- free heap;
- A2DP connection/playback stability;
- audible clicks, stalls or stale-buffer repetition.

The decisive requirement is not merely “DSP average below 100%.” The whole physical playback path must remain clean.

## Stage 5 — real-time failsafe validation

The normal build has:

```text
JANUS_PYRAMID_DSP_FAILSAFE = 1
JANUS_PYRAMID_DSP_OVER_BUDGET_TRIP = 3
```

The guard watches actual processing time per PCM block. Three consecutive DSP blocks with:

```text
DSP_PROCESS_TIME_US >= PCM_BLOCK_BUDGET_US
```

trip the physical layer into dry bypass.

Expected Serial event:

```text
PYRAMID_LANGUAGE_FAILSAFE | DRY_BYPASS reason=DSP_OVER_BUDGET ...
```

After a trip:

- future audio must continue dry;
- the DSP must remain disabled instead of repeatedly thrashing;
- canonical language parameters must remain unchanged;
- `PYR?` must show failsafe/trip state;
- `PYR=ON` may be used deliberately to clear the trip and retry.

Do **not** intentionally overload the system merely to force a trip if normal operation does not produce one. This stage can remain `NOT_TRIGGERED_IN_NORMAL_RUN`, which is a good outcome.

## Stage 6 — spoken JANUS voice

Repeat the A/B ladder with JANUS speech rather than only music.

Use one fixed sentence or paragraph generated by the current upstream larynx. The larynx and Pyramid Language are separate authorities:

```text
TEXT -> LARYNX/TTS -> ORDINARY PCM -> PYRAMID LANGUAGE -> SPEAKER
```

Evaluate:

- intelligibility;
- retained speaker identity/timbre;
- whether the 117–121 coloration masks low male speech fundamentals or vowels;
- whether room-tail duration blurs phrase boundaries;
- whether 25/50/75% depth gives a better physical listening result while 100% remains the canonical reference.

Do not change TTS voice and Pyramid depth simultaneously during A/B comparison.

## Stage 7 — microphone loopback smoke test

The repository contains a low-volume microphone smoke-test sketch. Acoustic feedback is possible, so this stage is not the first test and should be run at low volume with the device away from ears.

Goal:

```text
ES7210 mic -> PCM -> same Pyramid operator -> ES8311/AW87559 -> speaker
```

This confirms that the language operator is source-agnostic: Bluetooth, TTS, music and microphone PCM can share it.

## Acceptance record

For a hardware run, preserve a small receipt with at least:

```json
{
  "profile": "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2",
  "source_type": "BT_MUSIC | JANUS_TTS | MIC",
  "depth_percent": 100,
  "dsp_ema_us": 0,
  "dsp_peak_us": 0,
  "budget_us": 5804,
  "failsafe_trips": 0,
  "audio_drop_delta": 0,
  "free_heap_min": 0,
  "bt_disconnects": 0,
  "audible_stutter": false,
  "operator_judgement": "PASS | NEEDS_RUNTIME_DEPTH_TUNING | FAIL_REALTIME"
}
```

Replace zeros with observations; do not invent measurements.

## PASS gates

A physical run is `PASS_REALTIME` only when all of the following are observed:

1. source audio remains semantically/intelligibly the same source;
2. the effect is audible as a modeled acoustic coloration/space;
3. normal playback does not cause persistent queue drops or A2DP instability;
4. no repeated budget failsafe occurs under intended use;
5. heap remains viable for the existing swarm runtime;
6. `PYR=OFF/0/50/100` behaves predictably;
7. the canonical 117–121 language parameters were not altered to hide a performance problem.

Until a real device run provides those observations, firmware status should remain:

```text
CODE_PATH = IMPLEMENTED
HOST_REGRESSION = IMPLEMENTED
COMPOSE_PIPELINE = IMPLEMENTED
PHYSICAL_REALTIME_GATE = PENDING_DEVICE_MEASUREMENT
```
