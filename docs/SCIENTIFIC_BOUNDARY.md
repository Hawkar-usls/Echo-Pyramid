# Scientific boundary

`Echo-Pyramid` is allowed to be imaginative in presentation and strict in claims.

## What the embedded profile is

The default profile is a deterministic rectangular-room acoustic model inherited from `The-Voice-of-Janus`.

For chamber dimensions `Lx`, `Ly`, `Lz` and speed of sound `c`, air-acoustic modes are calculated as:

```text
f_pqr = (c / 2) * sqrt((p/Lx)^2 + (q/Ly)^2 + (r/Lz)^2)
```

The embedded ESP32 profile uses six derived render modes and a damped resonator bank to colour PCM audio.

## What it is not

It is not evidence that:

- the Great Pyramid was designed as an electronic/audio frequency generator;
- one special universal "pyramid frequency" exists;
- the current dimensions are an exact historical acoustic survey;
- predicted air modes are equivalent to measured resonances;
- air-acoustic modes are the same as stone/structural vibration modes;
- octave-translated render frequencies are physically present in the chamber.

Octave translation is a rendering operation. Metadata must retain the original physical mode.

## Evidence ladder

Use the following labels without collapsing them:

1. `ILLUSTRATIVE_MODEL_BASED` — geometry/model chosen for exploration.
2. `SOURCE_VERIFIED_GEOMETRY_MODEL` — dimensions and environmental assumptions tied to reliable sources, but acoustics still predicted.
3. `MEASURED_ROOM_RESPONSE` — microphone/excitation measurement or impulse response from the physical chamber with documented method.
4. `MEASURED_DEVICE_RESPONSE` — measurement of the Echo Pyramid hardware itself.

A higher rung does not retroactively turn a lower-rung object into measured evidence; preserve both artifacts and provenance.

## Hard rules

```text
MODEL_BASED_RECONSTRUCTION != MEASURED_HISTORICAL_SOUND
PREDICTED_MODAL_FREQUENCY != MEASURED_RESONANCE
AIR_ACOUSTIC_MODE != STRUCTURAL_VIBRATION_MODE
RENDER_FREQUENCY != CLAIM_OF_ANCIENT_INTENT
METAPHOR != PHYSICS
```

These rules are part of the machine-readable contract in `config/voice_contract.json` and should travel with future firmware profiles.
