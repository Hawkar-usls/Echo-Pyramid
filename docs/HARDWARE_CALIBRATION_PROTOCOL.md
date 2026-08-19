# Echo-Pyramid hardware calibration protocol

This protocol begins only after `docs/HARDWARE_TEST_PROTOCOL.md` establishes that the physical `PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3/ESP32-r2` runtime is stable enough to measure.

The calibration target is the **physical body** — Echo Pyramid enclosure, codec, amplifier, speaker and placement — not the semantic/acoustic language definition.

## Immutable boundary

```text
TEXT / MUSIC / MIC / TTS
        |
        v
PYRAMID LANGUAGE v0.3            <- language authority
        |
        v
PHYSICAL CALIBRATION             <- device/body authority
        |
        v
ES8311 -> AW87559 -> SPEAKER
```

The following values are language-locked for v0.3:

```text
117 / 119 / 121 Hz
Q = 29.75
anchor gain = +11.5 dB
anchor decay = 1.65 s
room decay = 0.78
wet = 0.72
dry = 0.62
room geometry = 10.45 x 5.20 x 5.80 m
```

If listening or measurement suggests changing any of those constants, record the result as a **LANGUAGE_RETUNE_CANDIDATE**. Do not apply it silently to v0.3. A real change requires a new Pyramid Language version and a new receipt.

## Phase A — realtime viability first

Before frequency-response calibration, confirm:

- stable Bluetooth playback;
- no persistent queue-drop growth;
- viable free heap;
- no repeating DSP budget failsafe;
- predictable `PYR=OFF/0/50/100` behavior.

If these fail, fix scheduling/implementation first. Do not compensate CPU problems acoustically.

## Phase B — listening-depth preference

Use a fixed speech sample and a fixed music sample. Keep source volume unchanged.

Compare:

```text
PYR=0
PYR=25
PYR=50
PYR=75
PYR=100
```

Record a preferred **runtime depth** for each source class. This does not redefine v0.3; `100%` remains the canonical reference.

Suggested receipt fields:

```text
source_type
source_id_or_hash
phone_volume
preferred_depth_percent
intelligibility_notes
low_voice_masking_notes
room_tail_notes
```

## Phase C — level matching

Compare `PYR=OFF` with `PYR=0` and `PYR=100` using the same source.

A physical post-language `output_trim_percent` may be used for safe level matching only. Start from the neutral value `100%`.

Do not alter anchor gain or dry/wet merely to equalize loudness; those are language parameters.

## Phase D — measured device response

Speaker/enclosure EQ must remain disabled until a measured response exists.

Preferred measurement path:

```text
known broadband test source
 -> same PCM transport
 -> Echo Pyramid output
 -> fixed microphone position
 -> recorded response
 -> device/enclosure response estimate
```

Keep the microphone, distance, orientation, room and device placement fixed across repeated measurements.

The goal is to identify repeatable **device/body coloration**, not room folklore or an assumed pyramid frequency.

Store at least:

```text
measurement_date
firmware/profile id
source signal id/hash
microphone/device used
microphone distance/orientation
room/placement notes
sample rate
measured response artifact id/hash
```

## Phase E — speaker compensation EQ

Only after a repeatable device response exists may a physical compensation EQ be proposed.

The compensation must be:

- explicitly post-language;
- traceable to a measured response;
- bounded and conservative;
- reversible;
- stored as a new calibration receipt;
- disabled by default until verified on-device.

It must not be used to creatively reshape the canonical 117/119/121 operator.

## Phase F — language-retune candidates

If the real enclosure repeatedly reveals that the canonical language itself would benefit from different `Q`, `gain`, `decay`, `wet`, `dry` or resonator values, freeze the observation as a candidate:

```json
{
  "status": "LANGUAGE_RETUNE_CANDIDATE",
  "base_language": "PYRAMID_LANGUAGE_117_121_ANCHORED_SPACE_v0.3",
  "candidate_change": {},
  "evidence": [],
  "applied_to_v0_3": false
}
```

Only a separately reviewed successor such as `v0.4` may adopt those changes.

## Calibration state machine

```text
PENDING_DEVICE_MEASUREMENT
        |
        v
REALTIME_PASS
        |
        v
DEPTH_AND_LEVEL_OBSERVED
        |
        v
DEVICE_RESPONSE_MEASURED
        |
        v
PHYSICAL_COMPENSATION_CANDIDATE
        |
        v
PHYSICAL_CALIBRATION_VERIFIED
```

Language-retune work branches separately:

```text
OBSERVATION
 -> LANGUAGE_RETUNE_CANDIDATE
 -> NEW_LANGUAGE_VERSION
```

## Core rule

```text
CALIBRATE_THE_BODY_WITHOUT_SILENTLY_REWRITING_THE_LANGUAGE
```
